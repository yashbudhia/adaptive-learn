import faiss
import numpy as np
import os
import pickle
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import logging
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from app.config import settings
from app.models import GameContext, BossAction
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FAISSService:
    """Service for managing FAISS vector indexes with real-time optimization"""
    
    def __init__(self):
        self.dimension = settings.embedding_dimension
        self.index_path = Path(settings.faiss_index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.indexes: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
        self.index_locks: Dict[str, threading.RLock] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Real-time optimization settings
        self.auto_optimize_threshold = 100  # Optimize after 100 new entries
        self.entry_counts: Dict[str, int] = {}
    
    def get_or_create_index(self, game_id: str) -> faiss.Index:
        """Get existing index or create new one for a game"""
        if game_id not in self.indexes:
            # Create lock for this game if it doesn't exist
            if game_id not in self.index_locks:
                self.index_locks[game_id] = threading.RLock()
            
            with self.index_locks[game_id]:
                # Double-check after acquiring lock
                if game_id not in self.indexes:
                    index_file = self.index_path / f"{game_id}.index"
                    metadata_file = self.index_path / f"{game_id}.metadata"
                    
                    if index_file.exists() and metadata_file.exists():
                        # Load existing index
                        try:
                            self.indexes[game_id] = faiss.read_index(str(index_file))
                            with open(metadata_file, 'rb') as f:
                                self.metadata[game_id] = pickle.load(f)
                            logger.info(f"Loaded existing FAISS index for game {game_id}")
                        except Exception as e:
                            logger.error(f"Error loading index for {game_id}: {str(e)}")
                            # Create new index if loading fails
                            self._create_new_index(game_id)
                    else:
                        # Create new index
                        self._create_new_index(game_id)
                    
                    self.entry_counts[game_id] = len(self.metadata.get(game_id, []))
        
        return self.indexes[game_id]
    
    def _create_new_index(self, game_id: str):
        """Create a new FAISS index for a game"""
        # Use IndexFlatIP for cosine similarity (after L2 normalization)
        # For larger datasets, consider IndexIVFFlat or IndexHNSWFlat
        if self.dimension <= 512:
            # For smaller dimensions, use flat index
            self.indexes[game_id] = faiss.IndexFlatIP(self.dimension)
        else:
            # For larger dimensions, use HNSW for better performance
            self.indexes[game_id] = faiss.IndexHNSWFlat(self.dimension, 32)
            self.indexes[game_id].hnsw.efConstruction = 200
            self.indexes[game_id].hnsw.efSearch = 50
        
        self.metadata[game_id] = []
        logger.info(f"Created new FAISS index for game {game_id}")
    
    def add_context(self, game_id: str, context_id: int, embedding: np.ndarray, 
                   context_data: Dict[str, Any], effectiveness_score: float = 0.0):
        """Add a context embedding to the index"""
        try:
            index = self.get_or_create_index(game_id)
            
            with self.index_locks[game_id]:
                # Normalize embedding for cosine similarity
                embedding = embedding.astype(np.float32)
                embedding_normalized = embedding.copy()
                faiss.normalize_L2(embedding_normalized.reshape(1, -1))
                
                # Add to index
                index.add(embedding_normalized.reshape(1, -1))
                
                # Store metadata
                metadata_entry = {
                    'context_id': context_id,
                    'context_data': context_data,
                    'effectiveness_score': effectiveness_score,
                    'index_position': index.ntotal - 1,
                    'embedding_quality': self._calculate_embedding_quality(embedding)
                }
                self.metadata[game_id].append(metadata_entry)
                
                # Update entry count
                self.entry_counts[game_id] = self.entry_counts.get(game_id, 0) + 1
                
                # Save to disk
                self._save_index(game_id)
                
                # Check if auto-optimization is needed
                if self.entry_counts[game_id] % self.auto_optimize_threshold == 0:
                    asyncio.create_task(self._auto_optimize_index(game_id))
                
                logger.info(f"Added context {context_id} to FAISS index for game {game_id}")
        
        except Exception as e:
            logger.error(f"Error adding context to FAISS index: {str(e)}")
            raise
    
    async def add_context_async(self, game_id: str, context_id: int, embedding: np.ndarray,
                              context_data: Dict[str, Any], effectiveness_score: float = 0.0):
        """Async version of add_context"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor, self.add_context, game_id, context_id, 
            embedding, context_data, effectiveness_score
        )
    
    def search_similar_contexts(self, game_id: str, query_embedding: np.ndarray, 
                              k: int = 5, min_effectiveness: float = 0.3) -> List[Dict[str, Any]]:
        """Search for similar contexts in the index"""
        try:
            if game_id not in self.indexes:
                logger.warning(f"No index found for game {game_id}")
                return []
            
            index = self.indexes[game_id]
            if index.ntotal == 0:
                logger.warning(f"Empty index for game {game_id}")
                return []
            
            with self.index_locks[game_id]:
                # Normalize query embedding
                query_embedding = query_embedding.astype(np.float32)
                query_normalized = query_embedding.copy()
                faiss.normalize_L2(query_normalized.reshape(1, -1))
                
                # Search with more candidates than needed for filtering
                search_k = min(k * 3, index.ntotal)
                scores, indices = index.search(query_normalized.reshape(1, -1), search_k)
                
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if idx == -1:  # Invalid index
                        continue
                    
                    if idx >= len(self.metadata[game_id]):
                        logger.warning(f"Index {idx} out of range for metadata")
                        continue
                    
                    metadata_entry = self.metadata[game_id][idx]
                    
                    # Filter by effectiveness score
                    if metadata_entry['effectiveness_score'] >= min_effectiveness:
                        result = {
                            'context_id': metadata_entry['context_id'],
                            'context_data': metadata_entry['context_data'],
                            'effectiveness_score': metadata_entry['effectiveness_score'],
                            'similarity_score': float(score),
                            'embedding_quality': metadata_entry.get('embedding_quality', 0.0),
                            'rank': len(results) + 1
                        }
                        results.append(result)
                        
                        # Stop when we have enough results
                        if len(results) >= k:
                            break
                
                logger.info(f"Found {len(results)} similar contexts for game {game_id}")
                return results
        
        except Exception as e:
            logger.error(f"Error searching FAISS index: {str(e)}")
            return []
    
    async def search_similar_contexts_async(self, game_id: str, query_embedding: np.ndarray,
                                          k: int = 5, min_effectiveness: float = 0.3) -> List[Dict[str, Any]]:
        """Async version of search_similar_contexts"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.search_similar_contexts, game_id, 
            query_embedding, k, min_effectiveness
        )
    
    def update_effectiveness_score(self, game_id: str, context_id: int, new_score: float):
        """Update the effectiveness score for a context"""
        try:
            if game_id not in self.metadata:
                logger.warning(f"No metadata found for game {game_id}")
                return
            
            with self.index_locks[game_id]:
                # Find and update the metadata entry
                updated = False
                for entry in self.metadata[game_id]:
                    if entry['context_id'] == context_id:
                        old_score = entry['effectiveness_score']
                        entry['effectiveness_score'] = new_score
                        self._save_metadata(game_id)
                        logger.info(f"Updated effectiveness score for context {context_id}: {old_score:.3f} -> {new_score:.3f}")
                        updated = True
                        break
                
                if not updated:
                    logger.warning(f"Context {context_id} not found in metadata for game {game_id}")
        
        except Exception as e:
            logger.error(f"Error updating effectiveness score: {str(e)}")
    
    def batch_update_effectiveness_scores(self, game_id: str, updates: List[Tuple[int, float]]):
        """Batch update effectiveness scores"""
        try:
            if game_id not in self.metadata:
                logger.warning(f"No metadata found for game {game_id}")
                return
            
            with self.index_locks[game_id]:
                # Create lookup dict for faster updates
                update_dict = dict(updates)
                updated_count = 0
                
                for entry in self.metadata[game_id]:
                    context_id = entry['context_id']
                    if context_id in update_dict:
                        entry['effectiveness_score'] = update_dict[context_id]
                        updated_count += 1
                
                if updated_count > 0:
                    self._save_metadata(game_id)
                    logger.info(f"Batch updated {updated_count} effectiveness scores for game {game_id}")
        
        except Exception as e:
            logger.error(f"Error batch updating effectiveness scores: {str(e)}")
    
    def remove_ineffective_contexts(self, game_id: str, min_effectiveness: float = 0.1):
        """Remove contexts with low effectiveness scores"""
        try:
            if game_id not in self.indexes or game_id not in self.metadata:
                return 0
            
            with self.index_locks[game_id]:
                # Find contexts to remove
                contexts_to_keep = []
                contexts_to_remove = []
                
                for i, entry in enumerate(self.metadata[game_id]):
                    if entry['effectiveness_score'] >= min_effectiveness:
                        contexts_to_keep.append(i)
                    else:
                        contexts_to_remove.append(i)
                
                if not contexts_to_remove:
                    return 0
                
                # Rebuild index without ineffective contexts
                old_index = self.indexes[game_id]
                old_metadata = self.metadata[game_id]
                
                # Create new index
                self._create_new_index(game_id)
                new_index = self.indexes[game_id]
                new_metadata = []
                
                # Add effective contexts to new index
                for i in contexts_to_keep:
                    try:
                        # Reconstruct embedding from old index
                        embedding = old_index.reconstruct(i).reshape(1, -1)
                        new_index.add(embedding)
                        
                        # Update metadata
                        metadata_entry = old_metadata[i].copy()
                        metadata_entry['index_position'] = new_index.ntotal - 1
                        new_metadata.append(metadata_entry)
                    except Exception as e:
                        logger.warning(f"Error reconstructing embedding at index {i}: {str(e)}")
                
                # Replace metadata
                self.metadata[game_id] = new_metadata
                
                # Save to disk
                self._save_index(game_id)
                
                removed_count = len(contexts_to_remove)
                logger.info(f"Removed {removed_count} ineffective contexts from game {game_id}")
                return removed_count
        
        except Exception as e:
            logger.error(f"Error removing ineffective contexts: {str(e)}")
            return 0
    
    async def _auto_optimize_index(self, game_id: str):
        """Auto-optimize index in background"""
        try:
            logger.info(f"Starting auto-optimization for game {game_id}")
            
            # Remove ineffective contexts
            removed = await asyncio.get_event_loop().run_in_executor(
                self.executor, self.remove_ineffective_contexts, game_id, 0.2
            )
            
            if removed > 0:
                logger.info(f"Auto-optimization removed {removed} ineffective contexts for game {game_id}")
        
        except Exception as e:
            logger.error(f"Error in auto-optimization for game {game_id}: {str(e)}")
    
    def get_index_stats(self, game_id: str) -> Dict[str, Any]:
        """Get statistics about the index"""
        try:
            if game_id not in self.indexes:
                return {'total_contexts': 0, 'avg_effectiveness': 0.0}
            
            index = self.indexes[game_id]
            metadata = self.metadata.get(game_id, [])
            
            if not metadata:
                return {'total_contexts': 0, 'avg_effectiveness': 0.0}
            
            effectiveness_scores = [entry['effectiveness_score'] for entry in metadata]
            embedding_qualities = [entry.get('embedding_quality', 0.0) for entry in metadata]
            
            return {
                'total_contexts': index.ntotal,
                'metadata_entries': len(metadata),
                'avg_effectiveness': np.mean(effectiveness_scores),
                'max_effectiveness': np.max(effectiveness_scores),
                'min_effectiveness': np.min(effectiveness_scores),
                'effectiveness_std': np.std(effectiveness_scores),
                'avg_embedding_quality': np.mean(embedding_qualities),
                'index_type': type(index).__name__,
                'dimension': self.dimension,
                'memory_usage_mb': self._estimate_memory_usage(index)
            }
        
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {'total_contexts': 0, 'avg_effectiveness': 0.0}
    
    def _estimate_memory_usage(self, index: faiss.Index) -> float:
        """Estimate memory usage of FAISS index in MB"""
        try:
            # Rough estimation based on index type and size
            if isinstance(index, faiss.IndexFlatIP):
                # Flat index: ntotal * dimension * 4 bytes (float32)
                return (index.ntotal * self.dimension * 4) / (1024 * 1024)
            elif isinstance(index, faiss.IndexHNSWFlat):
                # HNSW index: roughly 1.5x the flat index size
                return (index.ntotal * self.dimension * 4 * 1.5) / (1024 * 1024)
            else:
                # Default estimation
                return (index.ntotal * self.dimension * 4) / (1024 * 1024)
        except:
            return 0.0
    
    def _calculate_embedding_quality(self, embedding: np.ndarray) -> float:
        """Calculate quality score for an embedding"""
        try:
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm == 0:
                return 0.0
            
            normalized = embedding / norm
            
            # Calculate variance (higher is usually better)
            variance = np.var(normalized)
            
            # Calculate sparsity (lower is usually better)
            sparsity = np.sum(np.abs(normalized) < 1e-6) / len(normalized)
            
            # Combine into quality score
            quality = min(variance * 10, 1.0) * (1.0 - sparsity)
            return float(quality)
        
        except:
            return 0.0
    
    def _save_index(self, game_id: str):
        """Save index and metadata to disk"""
        try:
            index_file = self.index_path / f"{game_id}.index"
            faiss.write_index(self.indexes[game_id], str(index_file))
            self._save_metadata(game_id)
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")
    
    def _save_metadata(self, game_id: str):
        """Save metadata to disk"""
        try:
            metadata_file = self.index_path / f"{game_id}.metadata"
            with open(metadata_file, 'wb') as f:
                pickle.dump(self.metadata[game_id], f)
        except Exception as e:
            logger.error(f"Error saving metadata: {str(e)}")
    
    def rebuild_index_from_db(self, game_id: str, db: Session):
        """Rebuild FAISS index from database data"""
        try:
            from app.models import GameContext, BossAction
            
            # Get all contexts with their effectiveness scores
            contexts = db.query(GameContext).filter(
                GameContext.game_id == game_id
            ).all()
            
            if not contexts:
                logger.info(f"No contexts found for game {game_id}")
                return
            
            with self.index_locks.get(game_id, threading.RLock()):
                # Create new index
                self._create_new_index(game_id)
                new_index = self.indexes[game_id]
                new_metadata = []
                
                for context in contexts:
                    if context.embedding_vector:
                        try:
                            # Deserialize embedding
                            embedding = np.frombuffer(
                                bytes.fromhex(context.embedding_vector), 
                                dtype=np.float32
                            )
                            
                            # Calculate average effectiveness score from actions
                            actions = db.query(BossAction).filter(
                                BossAction.context_id == context.id
                            ).all()
                            
                            if actions:
                                effectiveness_scores = [
                                    action.effectiveness_score for action in actions 
                                    if action.effectiveness_score is not None
                                ]
                                avg_effectiveness = np.mean(effectiveness_scores) if effectiveness_scores else 0.0
                            else:
                                avg_effectiveness = 0.0
                            
                            # Add to index
                            embedding_normalized = embedding.copy()
                            faiss.normalize_L2(embedding_normalized.reshape(1, -1))
                            new_index.add(embedding_normalized.reshape(1, -1))
                            
                            # Add metadata
                            metadata_entry = {
                                'context_id': context.id,
                                'context_data': context.player_context,
                                'effectiveness_score': avg_effectiveness,
                                'index_position': new_index.ntotal - 1,
                                'embedding_quality': self._calculate_embedding_quality(embedding)
                            }
                            new_metadata.append(metadata_entry)
                        
                        except Exception as e:
                            logger.warning(f"Error processing context {context.id}: {str(e)}")
                
                # Replace metadata
                self.metadata[game_id] = new_metadata
                
                # Save to disk
                self._save_index(game_id)
                
                logger.info(f"Rebuilt FAISS index for game {game_id} with {new_index.ntotal} contexts")
        
        except Exception as e:
            logger.error(f"Error rebuilding index from database: {str(e)}")
            raise