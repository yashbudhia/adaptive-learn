from typing import Dict, Any, List, Optional
import logging
import numpy as np
from sqlalchemy.orm import Session
from app.models import (
    Game, GameContext, BossAction, JigsawStackPrompt,
    PlayerContextData, BossActionRequest, BossActionResponse,
    ActionOutcomeData, GameActionOutcome
)
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FAISSService
from app.services.jigsawstack_service import JigsawStackService
from app.database import get_redis
import json
import time

logger = logging.getLogger(__name__)


class AdaptiveBossService:
    """Main service for adaptive boss behavior system"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.faiss_service = FAISSService()
        self.jigsawstack_service = JigsawStackService()
        self.redis_client = get_redis()
        
        # Cache settings
        self.cache_ttl = 3600  # 1 hour
        self.similarity_threshold = 0.7
        self.min_effectiveness_score = 0.3
        self.max_similar_contexts = 5
    
    def register_game(self, game_id: str, name: str, description: str, 
                     vocabulary: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Register a new game with the adaptive boss system"""
        try:
            # Check if game already exists
            existing_game = db.query(Game).filter(Game.game_id == game_id).first()
            if existing_game:
                return {
                    "success": False,
                    "message": "Game already registered",
                    "game_id": game_id
                }
            
            # Create JigsawStack prompt for this game
            prompt_engine_id = self.jigsawstack_service.create_boss_behavior_prompt(
                game_id, vocabulary
            )
            
            # Create game record
            game = Game(
                game_id=game_id,
                name=name,
                description=description,
                vocabulary=vocabulary
            )
            db.add(game)
            db.flush()
            
            # Create JigsawStack prompt record
            prompt_record = JigsawStackPrompt(
                game_id=game.id,
                prompt_engine_id=prompt_engine_id,
                prompt_name=f"{name}_boss_behavior",
                prompt_template="Boss behavior prompt for " + name,
                is_active=True
            )
            db.add(prompt_record)
            db.commit()
            
            # Initialize FAISS index for this game
            self.faiss_service.get_or_create_index(game_id)
            
            logger.info(f"Successfully registered game: {game_id}")
            
            return {
                "success": True,
                "message": "Game registered successfully",
                "game_id": game_id,
                "prompt_engine_id": prompt_engine_id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error registering game {game_id}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to register game: {str(e)}",
                "game_id": game_id
            }
    
    def generate_boss_action(self, request: BossActionRequest, db: Session) -> BossActionResponse:
        """Generate an adaptive boss action based on player context"""
        try:
            start_time = time.time()
            
            # Get game information
            game = db.query(Game).filter(Game.game_id == request.game_id).first()
            if not game:
                raise ValueError(f"Game {request.game_id} not found")
            
            # Get active prompt
            prompt = db.query(JigsawStackPrompt).filter(
                JigsawStackPrompt.game_id == game.id,
                JigsawStackPrompt.is_active == True
            ).first()
            
            if not prompt:
                raise ValueError(f"No active prompt found for game {request.game_id}")
            
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                logger.info("Returning cached boss action")
                return cached_response
            
            # Create embedding for current player context
            context_embedding = self.embedding_service.create_context_embedding(
                request.player_context
            )
            
            # Search for similar contexts
            similar_contexts = self.faiss_service.search_similar_contexts(
                request.game_id,
                context_embedding,
                k=self.max_similar_contexts,
                min_effectiveness=self.min_effectiveness_score
            )
            
            # Generate boss action using JigsawStack
            boss_action = self.jigsawstack_service.generate_boss_action(
                prompt.prompt_engine_id,
                request.player_context,
                similar_contexts,
                request.boss_health_percentage,
                request.battle_phase,
                request.environment_factors.get('environment', 'standard arena')
            )
            
            # Store context and action in database
            context_hash = self.embedding_service.create_context_hash(request.player_context)
            
            # Check if context already exists
            existing_context = db.query(GameContext).filter(
                GameContext.game_id == game.id,
                GameContext.context_hash == context_hash
            ).first()
            
            if not existing_context:
                # Create new context
                game_context = GameContext(
                    game_id=game.id,
                    context_hash=context_hash,
                    player_context=request.player_context.model_dump(),
                    embedding_vector=context_embedding.tobytes().hex()
                )
                db.add(game_context)
                db.flush()
                context_id = game_context.id
            else:
                context_id = existing_context.id
            
            # Store boss action
            boss_action_record = BossAction(
                game_id=game.id,
                context_id=context_id,
                action_data=boss_action.model_dump(),
                execution_time=time.time() - start_time
            )
            db.add(boss_action_record)
            db.commit()
            
            # Cache the response
            self._cache_response(cache_key, boss_action)
            
            logger.info(f"Generated boss action for game {request.game_id} in {time.time() - start_time:.3f}s")
            
            return boss_action
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating boss action: {str(e)}")
            raise
    
    def log_action_outcome(self, action_outcome: ActionOutcomeData, db: Session):
        """Log the outcome of a boss action for learning"""
        try:
            # Get the action record
            action = db.query(BossAction).filter(BossAction.id == action_outcome.action_id).first()
            if not action:
                raise ValueError(f"Action {action_outcome.action_id} not found")
            
            # Update action with outcome data
            action.outcome = action_outcome.outcome.value
            action.effectiveness_score = action_outcome.effectiveness_score
            action.damage_dealt = action_outcome.damage_dealt
            action.player_hit = action_outcome.player_hit
            
            # Get game information
            game = db.query(Game).filter(Game.id == action.game_id).first()
            if not game:
                raise ValueError("Game not found")
            
            # Update FAISS index with effectiveness score if action was effective
            if action_outcome.effectiveness_score >= self.min_effectiveness_score:
                context = db.query(GameContext).filter(GameContext.id == action.context_id).first()
                if context and context.embedding_vector:
                    # Deserialize embedding
                    embedding = np.frombuffer(
                        bytes.fromhex(context.embedding_vector), 
                        dtype=np.float32
                    )
                    
                    # Add or update in FAISS index
                    self.faiss_service.add_context(
                        game.game_id,
                        context.id,
                        embedding,
                        context.player_context,
                        action_outcome.effectiveness_score
                    )
            
            db.commit()
            
            # Clear related cache entries
            self._invalidate_cache_for_game(game.game_id)
            
            logger.info(f"Logged action outcome: {action_outcome.outcome.value} "
                       f"(effectiveness: {action_outcome.effectiveness_score:.2f})")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error logging action outcome: {str(e)}")
            raise
    
    def get_game_stats(self, game_id: str, db: Session) -> Dict[str, Any]:
        """Get statistics for a game's adaptive behavior system"""
        try:
            game = db.query(Game).filter(Game.game_id == game_id).first()
            if not game:
                raise ValueError(f"Game {game_id} not found")
            
            # Get database stats
            total_contexts = db.query(GameContext).filter(GameContext.game_id == game.id).count()
            total_actions = db.query(BossAction).filter(BossAction.game_id == game.id).count()
            
            # Get effectiveness stats
            actions_with_outcomes = db.query(BossAction).filter(
                BossAction.game_id == game.id,
                BossAction.effectiveness_score.isnot(None)
            ).all()
            
            if actions_with_outcomes:
                effectiveness_scores = [action.effectiveness_score for action in actions_with_outcomes]
                avg_effectiveness = np.mean(effectiveness_scores)
                success_rate = len([s for s in effectiveness_scores if s >= 0.5]) / len(effectiveness_scores)
            else:
                avg_effectiveness = 0.0
                success_rate = 0.0
            
            # Get FAISS index stats
            faiss_stats = self.faiss_service.get_index_stats(game_id)
            
            # Get recent performance
            recent_actions = db.query(BossAction).filter(
                BossAction.game_id == game.id,
                BossAction.effectiveness_score.isnot(None)
            ).order_by(BossAction.created_at.desc()).limit(10).all()
            
            recent_effectiveness = 0.0
            if recent_actions:
                recent_effectiveness = np.mean([action.effectiveness_score for action in recent_actions])
            
            return {
                "game_id": game_id,
                "total_contexts": total_contexts,
                "total_actions": total_actions,
                "avg_effectiveness": avg_effectiveness,
                "success_rate": success_rate,
                "recent_effectiveness": recent_effectiveness,
                "faiss_stats": faiss_stats,
                "learning_progress": {
                    "contexts_in_index": faiss_stats.get('total_contexts', 0),
                    "avg_context_effectiveness": faiss_stats.get('avg_effectiveness', 0.0),
                    "improvement_trend": recent_effectiveness - avg_effectiveness
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting game stats: {str(e)}")
            raise
    
    def optimize_game_index(self, game_id: str, db: Session):
        """Optimize the FAISS index for a game by removing ineffective contexts"""
        try:
            game = db.query(Game).filter(Game.game_id == game_id).first()
            if not game:
                raise ValueError(f"Game {game_id} not found")
            
            # Remove ineffective contexts from FAISS
            self.faiss_service.remove_ineffective_contexts(
                game_id, 
                min_effectiveness=self.min_effectiveness_score
            )
            
            # Rebuild index from database if needed
            self.faiss_service.rebuild_index_from_db(game_id, db)
            
            logger.info(f"Optimized FAISS index for game {game_id}")
            
        except Exception as e:
            logger.error(f"Error optimizing game index: {str(e)}")
            raise
    
    def _generate_cache_key(self, request: BossActionRequest) -> str:
        """Generate cache key for a boss action request"""
        context_hash = self.embedding_service.create_context_hash(request.player_context)
        return f"boss_action:{request.game_id}:{context_hash}:{request.battle_phase}"
    
    def _get_cached_response(self, cache_key: str) -> Optional[BossActionResponse]:
        """Get cached boss action response"""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return BossActionResponse(**data)
            return None
        except Exception as e:
            logger.warning(f"Error getting cached response: {str(e)}")
            return None
    
    def _cache_response(self, cache_key: str, response: BossActionResponse):
        """Cache boss action response"""
        try:
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(response.model_dump())
            )
        except Exception as e:
            logger.warning(f"Error caching response: {str(e)}")
    
    def _invalidate_cache_for_game(self, game_id: str):
        """Invalidate all cached responses for a game"""
        try:
            pattern = f"boss_action:{game_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for game {game_id}")
        except Exception as e:
            logger.warning(f"Error invalidating cache: {str(e)}")