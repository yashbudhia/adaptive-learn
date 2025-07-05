import faiss
import numpy as np
import os
import pickle
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import logging
from app.config import settings
from app.models import GameContext, BossAction
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FAISSService:
    """Service for managing FAISS vector indexes"""
    
    def __init__(self):
        self.dimension = settings.embedding_dimension
        self.index_path = Path(settings.faiss_index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.indexes: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
    
    def get_or_create_index(self, game_id: str) -> faiss.Index:
        """Get existing index or create new one for a game"""
        if game_id not in self.indexes:
            index_file = self.index_path / f"{game_id}.index"
            metadata_file = self.index_path / f"{game_id}.metadata"
            
            if index_file.exists() and metadata_file.exists():
                # Load existing index
                self.indexes[game_id] = faiss.read_index(str(index_file))
                with open(metadata_file, 'rb') as f:
                    self.metadata[game_id] = pickle.load(f)
                logger.info(f"Loaded existing FAISS index for game {game_id}")
            else:
                # Create new index
                self.indexes[game_id] = faiss.IndexFlatIP(self.dimension)  # Inner Product for cosine similarity
                self.metadata[game_id] = []
                logger.info(f"Created new FAISS index for game {game_id}")
        
        return self.indexes[game_id]
    
    def add_context(self, game_id: str, context_id: int, embedding: np.ndarray, 
                   context_data: Dict[str, Any], effectiveness_score: float = 0.0):
        """Add a context embedding to the index"""
        try:
            index = self.get_or_create_index(game_id)
            
            # Normalize embedding for cosine similarity
            embedding = embedding.astype(np.float32)
            faiss.normalize_L2(embedding.reshape(1, -1))
            
            # Add to index
            index.add(embedding.reshape(1, -1))
            
            # Store metadata
            metadata_entry = {
                'context_id': context_id,
                'context_data': context_data,
                'effectiveness_score': effectiveness_score,
                'index_position': index.ntotal - 1
            }
            self.metadata[game_id].append(metadata_entry)
            
            # Save to disk
            self._save_index(game_id)
            
            logger.info(f"Added context {context_id} to FAISS index for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error adding context to FAISS index: {str(e)}")
            raise
    
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
            
            # Normalize query embedding
            query_embedding = query_embedding.astype(np.float32)
            faiss.normalize_L2(query_embedding.reshape(1, -1))
            
            # Search
            scores, indices = index.search(query_embedding.reshape(1, -1), min(k, index.ntotal))
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # Invalid index
                    continue
                
                metadata_entry = self.metadata[game_id][idx]
                
                # Filter by effectiveness score
                if metadata_entry['effectiveness_score'] >= min_effectiveness:
                    result = {
                        'context_id': metadata_entry['context_id'],
                        'context_data': metadata_entry['context_data'],
                        'effectiveness_score': metadata_entry['effectiveness_score'],
                        'similarity_score': float(score),
                        'rank': i + 1
                    }
                    results.append(result)
            
            logger.info(f"Found {len(results)} similar contexts for game {game_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error searching FAISS index: {str(e)}")
            return []
    
    def update_effectiveness_score(self, game_id: str, context_id: int, new_score: float):
        """Update the effectiveness score for a context"""
        try:
            if game_id not in self.metadata:
                logger.warning(f"No metadata found for game {game_id}")
                return
            
            # Find and update the metadata entry
            for entry in self.metadata[game_id]:
                if entry['context_id'] == context_id:
                    entry['effectiveness_score'] = new_score
                    self._save_metadata(game_id)
                    logger.info(f"Updated effectiveness score for context {context_id} to {new_score}")
                    return
            
            logger.warning(f"Context {context_id} not found in metadata for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error updating effectiveness score: {str(e)}")
    
    def remove_ineffective_contexts(self, game_id: str, min_effectiveness: float = 0.1):
        """Remove contexts with low effectiveness scores"""
        try:
            if game_id not in self.indexes or game_id not in self.metadata:
                return
            
            # Find contexts to remove
            contexts_to_remove = []
            for i, entry in enumerate(self.metadata[game_id]):
                if entry['effectiveness_score'] < min_effectiveness:
                    contexts_to_remove.append(i)
            
            if not contexts_to_remove:
                return
            
            # Rebuild index without ineffective contexts
            old_index = self.indexes[game_id]
            old_metadata = self.metadata[game_id]
            
            # Create new index
            new_index = faiss.IndexFlatIP(self.dimension)
            new_metadata = []
            
            for i in range(len(old_metadata)):
                if i not in contexts_to_remove:
                    # Get embedding from old index
                    embedding = old_index.reconstruct(i).reshape(1, -1)
                    new_index.add(embedding)
                    
                    # Update metadata
                    metadata_entry = old_metadata[i].copy()
                    metadata_entry['index_position'] = new_index.ntotal - 1
                    new_metadata.append(metadata_entry)
            
            # Replace old index and metadata
            self.indexes[game_id] = new_index
            self.metadata[game_id] = new_metadata
            
            # Save to disk
            self._save_index(game_id)
            
            logger.info(f"Removed {len(contexts_to_remove)} ineffective contexts from game {game_id}")
            
        except Exception as e:
            logger.error(f"Error removing ineffective contexts: {str(e)}")
    
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
            
            return {
                'total_contexts': index.ntotal,
                'avg_effectiveness': np.mean(effectiveness_scores),
                'max_effectiveness': np.max(effectiveness_scores),
                'min_effectiveness': np.min(effectiveness_scores),
                'effectiveness_std': np.std(effectiveness_scores)
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {'total_contexts': 0, 'avg_effectiveness': 0.0}
    
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
            
            # Create new index
            new_index = faiss.IndexFlatIP(self.dimension)
            new_metadata = []
            
            for context in contexts:
                if context.embedding_vector:
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
                        avg_effectiveness = np.mean([action.effectiveness_score for action in actions])
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
                        'index_position': new_index.ntotal - 1
                    }
                    new_metadata.append(metadata_entry)
            
            # Replace index and metadata
            self.indexes[game_id] = new_index
            self.metadata[game_id] = new_metadata
            
            # Save to disk
            self._save_index(game_id)
            
            logger.info(f"Rebuilt FAISS index for game {game_id} with {new_index.ntotal} contexts")
            
        except Exception as e:
            logger.error(f"Error rebuilding index from database: {str(e)}")
            raise