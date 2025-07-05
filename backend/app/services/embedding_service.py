import openai
import numpy as np
from typing import List, Dict, Any
import json
import hashlib
from app.config import settings
from app.models import PlayerContextData
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = "text-embedding-ada-002"
        self.dimension = settings.embedding_dimension
    
    def create_context_embedding(self, player_context: PlayerContextData) -> np.ndarray:
        """Create embedding from player context data"""
        try:
            # Convert player context to a structured text representation
            context_text = self._context_to_text(player_context)
            
            # Generate embedding
            response = openai.embeddings.create(
                model=self.model,
                input=context_text
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            logger.info(f"Generated embedding with dimension: {embedding.shape}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error creating embedding: {str(e)}")
            raise
    
    def create_context_hash(self, player_context: PlayerContextData) -> str:
        """Create a hash of the player context for quick lookup"""
        context_dict = player_context.model_dump()
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
            # Convert all contexts to text
            context_texts = [self._context_to_text(context) for context in contexts]
            
            # Generate embeddings in batch
            response = openai.embeddings.create(
                model=self.model,
                input=context_texts
            )
            
            embeddings = []
            for data in response.data:
                embedding = np.array(data.embedding, dtype=np.float32)
                embeddings.append(embedding)
            
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error creating batch embeddings: {str(e)}")
            raise