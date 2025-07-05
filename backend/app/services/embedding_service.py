import openai
import numpy as np
from typing import List, Dict, Any
import json
import hashlib
from app.config import settings
from app.models import PlayerContextData
import logging
import asyncio
import time

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI with real-time optimization"""
    
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = "text-embedding-ada-002"
        self.dimension = settings.embedding_dimension
        self.cache = {}  # Simple in-memory cache for embeddings
        self.cache_ttl = 3600  # 1 hour
        self.batch_size = 100  # Maximum batch size for OpenAI
    
    def create_context_embedding(self, player_context: PlayerContextData) -> np.ndarray:
        """Create embedding from player context data with caching"""
        try:
            # Create cache key
            context_hash = self.create_context_hash(player_context)
            
            # Check cache first
            if context_hash in self.cache:
                cache_entry = self.cache[context_hash]
                if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                    logger.debug(f"Using cached embedding for context {context_hash[:16]}...")
                    return cache_entry['embedding']
                else:
                    # Remove expired entry
                    del self.cache[context_hash]
            
            # Convert player context to a structured text representation
            context_text = self._context_to_text(player_context)
            
            # Generate embedding
            response = openai.embeddings.create(
                model=self.model,
                input=context_text
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Cache the embedding
            self.cache[context_hash] = {
                'embedding': embedding,
                'timestamp': time.time()
            }
            
            logger.info(f"Generated embedding with dimension: {embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    async def create_context_embedding_async(self, player_context: PlayerContextData) -> np.ndarray:
        """Async version of create_context_embedding"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.create_context_embedding, player_context)
    
    def create_context_hash(self, player_context: PlayerContextData) -> str:
        """Create a hash of the player context for quick lookup"""
        context_dict = player_context.dict()
        context_str = json.dumps(context_dict, sort_keys=True)
        return hashlib.sha256(context_str.encode()).hexdigest()
    
    def _context_to_text(self, player_context: PlayerContextData) -> str:
        """Convert player context to structured text for embedding"""
        text_parts = []
        
        # Player actions and patterns
        text_parts.append(f"Player frequently performs: {', '.join(player_context.frequent_actions)}")
        text_parts.append(f"Dodge frequency: {player_context.dodge_frequency:.2f}")
        text_parts.append(f"Attack patterns: {', '.join(player_context.attack_patterns)}")
        text_parts.append(f"Movement style: {player_context.movement_style}")
        
        # Player state
        text_parts.append(f"Reaction time: {player_context.reaction_time:.2f} seconds")
        text_parts.append(f"Health: {player_context.health_percentage:.1%}")
        text_parts.append(f"Difficulty preference: {player_context.difficulty_preference}")
        
        # Session context
        text_parts.append(f"Session duration: {player_context.session_duration:.1f} minutes")
        text_parts.append(f"Recent deaths: {player_context.recent_deaths}")
        text_parts.append(f"Equipment level: {player_context.equipment_level}")
        
        # Additional context
        if player_context.additional_context:
            for key, value in player_context.additional_context.items():
                text_parts.append(f"{key}: {value}")
        
        return " | ".join(text_parts)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Normalize vectors
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    def batch_create_embeddings(self, contexts: List[PlayerContextData]) -> List[np.ndarray]:
        """Create embeddings for multiple contexts in batch"""
        try:
            if not contexts:
                return []
            
            # Split into batches if necessary
            all_embeddings = []
            for i in range(0, len(contexts), self.batch_size):
                batch_contexts = contexts[i:i + self.batch_size]
                batch_embeddings = self._process_embedding_batch(batch_contexts)
                all_embeddings.extend(batch_embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} embeddings in batch")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {str(e)}")
            raise
    
    def _process_embedding_batch(self, contexts: List[PlayerContextData]) -> List[np.ndarray]:
        """Process a single batch of embeddings"""
        # Check cache for existing embeddings
        embeddings = []
        contexts_to_process = []
        context_indices = []
        
        for i, context in enumerate(contexts):
            context_hash = self.create_context_hash(context)
            
            if context_hash in self.cache:
                cache_entry = self.cache[context_hash]
                if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                    embeddings.append((i, cache_entry['embedding']))
                    continue
            
            contexts_to_process.append(context)
            context_indices.append(i)
        
        # Process remaining contexts
        if contexts_to_process:
            # Convert all contexts to text
            context_texts = [self._context_to_text(context) for context in contexts_to_process]
            
            # Generate embeddings in batch
            response = openai.embeddings.create(
                model=self.model,
                input=context_texts
            )
            
            # Process results
            for j, (context, data) in enumerate(zip(contexts_to_process, response.data)):
                embedding = np.array(data.embedding, dtype=np.float32)
                original_index = context_indices[j]
                embeddings.append((original_index, embedding))
                
                # Cache the embedding
                context_hash = self.create_context_hash(context)
                self.cache[context_hash] = {
                    'embedding': embedding,
                    'timestamp': time.time()
                }
        
        # Sort by original index and return embeddings
        embeddings.sort(key=lambda x: x[0])
        return [embedding for _, embedding in embeddings]
    
    async def batch_create_embeddings_async(self, contexts: List[PlayerContextData]) -> List[np.ndarray]:
        """Async version of batch_create_embeddings"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch_create_embeddings, contexts)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics"""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for entry in self.cache.values():
            if current_time - entry['timestamp'] < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'cache_hit_rate': valid_entries / max(1, len(self.cache)),
            'memory_usage_mb': len(self.cache) * self.dimension * 4 / (1024 * 1024)  # Approximate
        }
    
    def clear_expired_cache(self):
        """Clear expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        logger.info(f"Cleared {len(expired_keys)} expired cache entries")
        return len(expired_keys)
    
    def precompute_embeddings(self, contexts: List[PlayerContextData]) -> Dict[str, np.ndarray]:
        """Precompute embeddings for a list of contexts"""
        embeddings_dict = {}
        
        try:
            embeddings = self.batch_create_embeddings(contexts)
            
            for context, embedding in zip(contexts, embeddings):
                context_hash = self.create_context_hash(context)
                embeddings_dict[context_hash] = embedding
            
            logger.info(f"Precomputed {len(embeddings_dict)} embeddings")
            
        except Exception as e:
            logger.error(f"Error precomputing embeddings: {str(e)}")
        
        return embeddings_dict
    
    def get_embedding_quality_score(self, embedding: np.ndarray) -> float:
        """Calculate a quality score for an embedding"""
        try:
            # Check for zero vectors
            if np.allclose(embedding, 0):
                return 0.0
            
            # Calculate norm (should be close to 1 for normalized embeddings)
            norm = np.linalg.norm(embedding)
            
            # Calculate variance (higher variance usually indicates better representation)
            variance = np.var(embedding)
            
            # Calculate sparsity (lower sparsity is usually better)
            sparsity = np.sum(np.abs(embedding) < 1e-6) / len(embedding)
            
            # Combine metrics into a quality score
            quality_score = (
                min(norm, 1.0) * 0.3 +  # Norm component
                min(variance * 100, 1.0) * 0.5 +  # Variance component
                (1.0 - sparsity) * 0.2  # Sparsity component
            )
            
            return float(quality_score)
            
        except Exception as e:
            logger.error(f"Error calculating embedding quality: {str(e)}")
            return 0.0