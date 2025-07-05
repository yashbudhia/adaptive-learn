from typing import Dict, Any, List, Optional
import logging
import numpy as np
import asyncio
import time
from sqlalchemy.orm import Session
from app.models import (
    Game, GameContext, BossAction, JigsawStackPrompt,
    PlayerContextData, BossActionRequest, BossActionResponse,
    ActionOutcomeData, GameActionOutcome
)
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FAISSService
from app.services.jigsawstack_service import JigsawStackService
from app.database import get_redis, realtime_cache
import json

logger = logging.getLogger(__name__)


class AdaptiveBossService:
    """Main service for adaptive boss behavior system with real-time capabilities"""
    
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
        
        # Real-time settings
        self.realtime_cache_ttl = 300  # 5 minutes
        self.performance_window = 100  # Track last 100 actions for performance
    
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
            
            # Initialize real-time cache for this game
            asyncio.create_task(self._initialize_game_cache(game_id))
            
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
    
    async def register_game_async(self, game_id: str, name: str, description: str,
                                vocabulary: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Async version of register_game"""
        try:
            # Check if game already exists
            existing_game = db.query(Game).filter(Game.game_id == game_id).first()
            if existing_game:
                return {
                    "success": False,
                    "message": "Game already registered",
                    "game_id": game_id
                }
            
            # Create JigsawStack prompt for this game (async)
            prompt_engine_id = await self.jigsawstack_service.create_boss_behavior_prompt_async(
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
            
            # Initialize real-time cache for this game
            await self._initialize_game_cache(game_id)
            
            logger.info(f"Successfully registered game async: {game_id}")
            
            return {
                "success": True,
                "message": "Game registered successfully",
                "game_id": game_id,
                "prompt_engine_id": prompt_engine_id
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error registering game async {game_id}: {str(e)}")
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
            
            # Check cache first (for non-realtime requests)
            if not request.realtime:
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
            
            # Prepare real-time factors
            realtime_factors = self._prepare_realtime_factors(request, similar_contexts)
            
            # Generate boss action using JigsawStack
            boss_action = self.jigsawstack_service.generate_boss_action(
                prompt.prompt_engine_id,
                request.player_context,
                similar_contexts,
                request.boss_health_percentage,
                request.battle_phase,
                request.environment_factors.get('environment', 'standard arena'),
                realtime_factors
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
                    player_context=request.player_context.dict(),
                    embedding_vector=context_embedding.tobytes().hex()
                )
                db.add(game_context)
                db.flush()
                context_id = game_context.id
            else:
                context_id = existing_context.id
                # Update usage count
                existing_context.usage_count += 1
            
            # Store boss action
            boss_action_record = BossAction(
                game_id=game.id,
                context_id=context_id,
                websocket_session_id=self._get_websocket_session_id(request.session_id, db) if request.session_id else None,
                action_data=boss_action.dict(),
                response_time=time.time() - start_time
            )
            db.add(boss_action_record)
            db.commit()
            
            # Add response metadata
            boss_action.response_time = time.time() - start_time
            boss_action.similar_contexts_used = len(similar_contexts)
            
            # Cache the response (for non-realtime requests)
            if not request.realtime:
                self._cache_response(cache_key, boss_action)
            
            # Update real-time cache
            if request.realtime:
                asyncio.create_task(self._update_realtime_cache(
                    request.game_id, boss_action_record.id, boss_action
                ))
            
            logger.info(f"Generated boss action for game {request.game_id} in {time.time() - start_time:.3f}s")
            
            return boss_action
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating boss action: {str(e)}")
            raise
    
    async def generate_boss_action_async(self, request: BossActionRequest, db: Session) -> BossActionResponse:
        """Async version of generate_boss_action for real-time WebSocket requests"""
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
            
            # Create embedding for current player context (async)
            context_embedding = await self.embedding_service.create_context_embedding_async(
                request.player_context
            )
            
            # Search for similar contexts (async)
            similar_contexts = await self.faiss_service.search_similar_contexts_async(
                request.game_id,
                context_embedding,
                k=self.max_similar_contexts,
                min_effectiveness=self.min_effectiveness_score
            )
            
            # Prepare real-time factors
            realtime_factors = await self._prepare_realtime_factors_async(request, similar_contexts)
            
            # Generate boss action using JigsawStack (async)
            boss_action = await self.jigsawstack_service.generate_boss_action_async(
                prompt.prompt_engine_id,
                request.player_context,
                similar_contexts,
                request.boss_health_percentage,
                request.battle_phase,
                request.environment_factors.get('environment', 'standard arena'),
                realtime_factors
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
                    player_context=request.player_context.dict(),
                    embedding_vector=context_embedding.tobytes().hex()
                )
                db.add(game_context)
                db.flush()
                context_id = game_context.id
            else:
                context_id = existing_context.id
                existing_context.usage_count += 1
            
            # Store boss action
            boss_action_record = BossAction(
                game_id=game.id,
                context_id=context_id,
                websocket_session_id=self._get_websocket_session_id(request.session_id, db) if request.session_id else None,
                action_data=boss_action.dict(),
                response_time=time.time() - start_time
            )
            db.add(boss_action_record)
            db.commit()
            
            # Add response metadata
            boss_action.response_time = time.time() - start_time
            boss_action.similar_contexts_used = len(similar_contexts)
            
            # Update real-time cache
            await self._update_realtime_cache(
                request.game_id, boss_action_record.id, boss_action
            )
            
            logger.info(f"Generated boss action async for game {request.game_id} in {time.time() - start_time:.3f}s")
            
            return boss_action
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating boss action async: {str(e)}")
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
            
            # Update context effectiveness
            context = db.query(GameContext).filter(GameContext.id == action.context_id).first()
            if context:
                # Update average effectiveness
                total_actions = db.query(BossAction).filter(
                    BossAction.context_id == context.id,
                    BossAction.effectiveness_score.isnot(None)
                ).count()
                
                if total_actions > 0:
                    avg_effectiveness = db.query(BossAction).filter(
                        BossAction.context_id == context.id,
                        BossAction.effectiveness_score.isnot(None)
                    ).with_entities(BossAction.effectiveness_score).all()
                    
                    context.avg_effectiveness = np.mean([score[0] for score in avg_effectiveness])
            
            # Update FAISS index with effectiveness score if action was effective
            if action_outcome.effectiveness_score >= self.min_effectiveness_score:
                if context and context.embedding_vector:
                    # Deserialize embedding
                    embedding = np.frombuffer(
                        bytes.fromhex(context.embedding_vector), 
                        dtype=np.float32
                    )
                    
                    # Add or update in FAISS index
                    asyncio.create_task(self.faiss_service.add_context_async(
                        game.game_id,
                        context.id,
                        embedding,
                        context.player_context,
                        action_outcome.effectiveness_score
                    ))
            
            db.commit()
            
            # Clear related cache entries
            self._invalidate_cache_for_game(game.game_id)
            
            # Update real-time performance tracking
            asyncio.create_task(self._update_performance_tracking(
                game.game_id, action_outcome.effectiveness_score
            ))
            
            logger.info(f"Logged action outcome: {action_outcome.outcome.value} "
                       f"(effectiveness: {action_outcome.effectiveness_score:.2f})")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error logging action outcome: {str(e)}")
            raise
    
    async def log_action_outcome_async(self, action_outcome: ActionOutcomeData, db: Session):
        """Async version of log_action_outcome"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.log_action_outcome, action_outcome, db)
    
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
            
            # Get real-time stats
            realtime_stats = asyncio.create_task(self._get_realtime_stats(game_id))
            
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
                },
                "realtime_performance": {
                    "avg_response_time": np.mean([action.response_time for action in recent_actions if action.response_time]) if recent_actions else 0.0,
                    "cache_hit_rate": self._calculate_cache_hit_rate(game_id)
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
            removed_count = self.faiss_service.remove_ineffective_contexts(
                game_id, 
                min_effectiveness=self.min_effectiveness_score
            )
            
            # Rebuild index from database if needed
            if removed_count > 0:
                self.faiss_service.rebuild_index_from_db(game_id, db)
            
            logger.info(f"Optimized FAISS index for game {game_id}, removed {removed_count} contexts")
            
        except Exception as e:
            logger.error(f"Error optimizing game index: {str(e)}")
            raise
    
    def _prepare_realtime_factors(self, request: BossActionRequest, 
                                similar_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare real-time factors for the prompt"""
        factors = {}
        
        # Player performance indicators
        if request.player_context.recent_deaths > 2:
            factors['player_struggling'] = True
        elif request.player_context.recent_deaths == 0 and request.player_context.health_percentage > 0.8:
            factors['player_dominating'] = True
        
        # Adaptation indicators
        if similar_contexts:
            avg_similarity = np.mean([ctx.get('similarity_score', 0) for ctx in similar_contexts])
            if avg_similarity > 0.9:
                factors['pattern_detected'] = True
        
        # Session factors
        if request.player_context.session_duration > 30:
            factors['long_session'] = True
        
        return factors
    
    async def _prepare_realtime_factors_async(self, request: BossActionRequest,
                                            similar_contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Async version of _prepare_realtime_factors"""
        # Get additional real-time data from cache
        game_performance = await realtime_cache.get_game_stats(request.game_id)
        
        factors = self._prepare_realtime_factors(request, similar_contexts)
        
        # Add real-time performance data
        if game_performance:
            factors['recent_avg_effectiveness'] = game_performance.get('avg_effectiveness', 0.0)
            factors['performance_trend'] = game_performance.get('performance_trend', 'stable')
        
        return factors
    
    async def _initialize_game_cache(self, game_id: str):
        """Initialize real-time cache for a game"""
        try:
            initial_stats = {
                'actions_count': 0,
                'avg_effectiveness': 0.0,
                'performance_trend': 'stable',
                'last_updated': time.time()
            }
            await realtime_cache.set_game_stats(game_id, initial_stats)
        except Exception as e:
            logger.error(f"Error initializing game cache: {str(e)}")
    
    async def _update_realtime_cache(self, game_id: str, action_id: int, boss_action: BossActionResponse):
        """Update real-time cache with new action data"""
        try:
            await realtime_cache.set_realtime_action(
                str(action_id), 
                boss_action.dict(), 
                ttl=self.realtime_cache_ttl
            )
        except Exception as e:
            logger.error(f"Error updating real-time cache: {str(e)}")
    
    async def _update_performance_tracking(self, game_id: str, effectiveness_score: float):
        """Update performance tracking metrics"""
        try:
            # Increment action counter
            await realtime_cache.increment_counter(f"actions:{game_id}")
            
            # Update effectiveness tracking
            current_stats = await realtime_cache.get_game_stats(game_id)
            if current_stats:
                actions_count = current_stats.get('actions_count', 0) + 1
                current_avg = current_stats.get('avg_effectiveness', 0.0)
                
                # Calculate new average
                new_avg = ((current_avg * (actions_count - 1)) + effectiveness_score) / actions_count
                
                # Determine trend
                trend = 'improving' if new_avg > current_avg else 'declining' if new_avg < current_avg else 'stable'
                
                updated_stats = {
                    'actions_count': actions_count,
                    'avg_effectiveness': new_avg,
                    'performance_trend': trend,
                    'last_updated': time.time()
                }
                
                await realtime_cache.set_game_stats(game_id, updated_stats)
        
        except Exception as e:
            logger.error(f"Error updating performance tracking: {str(e)}")
    
    async def _get_realtime_stats(self, game_id: str) -> Dict[str, Any]:
        """Get real-time statistics for a game"""
        try:
            return await realtime_cache.get_game_stats(game_id)
        except Exception as e:
            logger.error(f"Error getting real-time stats: {str(e)}")
            return {}
    
    def _get_websocket_session_id(self, session_id: str, db: Session) -> Optional[int]:
        """Get WebSocket session database ID"""
        if not session_id:
            return None
        
        try:
            from app.models import WebSocketSession
            ws_session = db.query(WebSocketSession).filter(
                WebSocketSession.session_id == session_id
            ).first()
            return ws_session.id if ws_session else None
        except Exception as e:
            logger.warning(f"Error getting WebSocket session ID: {str(e)}")
            return None
    
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
                json.dumps(response.dict())
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
    
    def _calculate_cache_hit_rate(self, game_id: str) -> float:
        """Calculate cache hit rate for a game"""
        try:
            # This would be implemented with proper cache metrics
            # For now, return a placeholder
            return 0.75
        except Exception as e:
            logger.warning(f"Error calculating cache hit rate: {str(e)}")
            return 0.0