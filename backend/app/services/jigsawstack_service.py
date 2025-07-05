import requests
import json
import asyncio
import aiohttp
import time
from typing import Dict, Any, List, Optional
import logging
from app.config import settings
from app.models import PlayerContextData, BossActionResponse

logger = logging.getLogger(__name__)


class JigsawStackService:
    """Service for interacting with JigsawStack Prompt Engine with async support"""
    
    def __init__(self):
        self.api_key = settings.jigsawstack_api_key
        self.base_url = "https://api.jigsawstack.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        self.session = None
        self.request_timeout = 30  # seconds
        self.max_retries = 3
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self.session
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def create_boss_behavior_prompt(self, game_id: str, game_vocabulary: Dict[str, Any]) -> str:
        """Create a game-specific boss behavior prompt template (sync version)"""
        try:
            # Extract game-specific elements
            actions = game_vocabulary.get('boss_actions', [])
            action_types = game_vocabulary.get('action_types', [])
            environments = game_vocabulary.get('environments', [])
            difficulty_levels = game_vocabulary.get('difficulty_levels', [])
            
            # Build the enhanced prompt template for real-time adaptation
            prompt_template = f"""
You are an adaptive AI boss in the game "{game_vocabulary.get('game_name', 'Unknown Game')}". 
Your goal is to provide challenging but fair gameplay that adapts to the player's behavior and skill level in real-time.

GAME CONTEXT:
- Available boss actions: {', '.join(actions)}
- Action types: {', '.join(action_types)}
- Environment factors: {', '.join(environments)}
- Difficulty levels: {', '.join(difficulty_levels)}

PLAYER CONTEXT:
{{player_context}}

SIMILAR PAST SITUATIONS:
{{similar_contexts}}

CURRENT BATTLE STATE:
- Boss health: {{boss_health}}%
- Battle phase: {{battle_phase}}
- Environment: {{environment}}
- Real-time factors: {{realtime_factors}}

ADAPTATION INSTRUCTIONS:
1. Analyze the player's current behavior patterns and skill level
2. Consider similar past situations and their effectiveness scores
3. Adapt to real-time changes in player performance
4. Choose an appropriate boss action that:
   - Matches the player's current skill level
   - Provides appropriate challenge without being unfair
   - Uses game-specific mechanics effectively
   - Considers the current battle context and environment
   - Adapts to the player's recent performance

5. Respond with a structured boss action that includes:
   - Primary action to execute
   - Action type and intensity (0.0 to 1.0)
   - Timing and positioning details
   - Expected player response
   - Reasoning for the choice
   - Confidence level in the action's effectiveness

REAL-TIME ADAPTATION RULES:
- If player is struggling (low health, many deaths): Reduce intensity by 10-20%
- If player is dominating (high health, no deaths): Increase intensity by 10-20%
- If player shows consistent patterns: Introduce counter-strategies
- If player adapts quickly: Vary tactics more frequently
- Always maintain engagement and fun as primary goals

Focus on creating engaging, adaptive gameplay that learns from past interactions and responds to real-time player behavior.
"""

            # Create the prompt in JigsawStack
            payload = {
                "prompt": prompt_template,
                "inputs": [
                    {
                        "key": "player_context",
                        "optional": False,
                        "initial_value": "Player context will be provided here"
                    },
                    {
                        "key": "similar_contexts",
                        "optional": True,
                        "initial_value": "No similar contexts found"
                    },
                    {
                        "key": "boss_health",
                        "optional": False,
                        "initial_value": "100"
                    },
                    {
                        "key": "battle_phase",
                        "optional": False,
                        "initial_value": "opening"
                    },
                    {
                        "key": "environment",
                        "optional": True,
                        "initial_value": "standard arena"
                    },
                    {
                        "key": "realtime_factors",
                        "optional": True,
                        "initial_value": "normal conditions"
                    }
                ],
                "return_prompt": {
                    "boss_action": "specific action to execute",
                    "action_type": "type of action (attack, defend, special, etc.)",
                    "intensity": "action intensity from 0.0 to 1.0",
                    "target_area": "where to target the action",
                    "duration": "action duration in seconds",
                    "cooldown": "cooldown before next action",
                    "animation_id": "animation identifier",
                    "sound_effects": ["list of sound effects"],
                    "visual_effects": ["list of visual effects"],
                    "damage_multiplier": "damage multiplier for this action",
                    "success_probability": "estimated success probability",
                    "confidence_level": "confidence in action effectiveness (0.0 to 1.0)",
                    "adaptation_reason": "why this action was chosen based on player behavior",
                    "counter_strategy": "how this action counters player patterns",
                    "reasoning": "detailed explanation of the decision"
                },
                "prompt_guard": [
                    "sexual_content",
                    "defamation",
                    "hate",
                    "violence_extreme"
                ],
                "optimize_prompt": True
            }
            
            response = requests.post(
                f"{self.base_url}/prompt_engine",
                headers=self.headers,
                json=payload,
                timeout=self.request_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_engine_id = result.get("prompt_engine_id")
                logger.info(f"Created boss behavior prompt for game {game_id}: {prompt_engine_id}")
                return prompt_engine_id
            else:
                logger.error(f"Failed to create prompt: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create prompt: {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating boss behavior prompt: {str(e)}")
            raise
    
    async def create_boss_behavior_prompt_async(self, game_id: str, game_vocabulary: Dict[str, Any]) -> str:
        """Async version of create_boss_behavior_prompt"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.create_boss_behavior_prompt, game_id, game_vocabulary)
    
    def generate_boss_action(self, prompt_engine_id: str, player_context: PlayerContextData,
                           similar_contexts: List[Dict[str, Any]], boss_health: float,
                           battle_phase: str, environment: str = "standard arena",
                           realtime_factors: Dict[str, Any] = None) -> BossActionResponse:
        """Generate a boss action using the prompt engine (sync version)"""
        try:
            # Format player context
            player_context_text = self._format_player_context(player_context)
            
            # Format similar contexts
            similar_contexts_text = self._format_similar_contexts(similar_contexts)
            
            # Format real-time factors
            realtime_factors_text = self._format_realtime_factors(realtime_factors or {})
            
            # Prepare input values
            input_values = {
                "player_context": player_context_text,
                "similar_contexts": similar_contexts_text,
                "boss_health": str(int(boss_health * 100)),
                "battle_phase": battle_phase,
                "environment": environment,
                "realtime_factors": realtime_factors_text
            }
            
            # Execute the prompt with retries
            for attempt in range(self.max_retries):
                try:
                    payload = {"input_values": input_values}
                    
                    response = requests.post(
                        f"{self.base_url}/prompt_engine/{prompt_engine_id}",
                        headers=self.headers,
                        json=payload,
                        timeout=self.request_timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        boss_action_data = result.get("result", {})
                        
                        # Parse and validate the response
                        boss_action = self._parse_boss_action_response(boss_action_data)
                        
                        logger.info(f"Generated boss action: {boss_action.boss_action} (attempt {attempt + 1})")
                        return boss_action
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"Failed to generate boss action after {self.max_retries} attempts: {response.text}")
                
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        raise Exception("Request timed out after multiple attempts")
                
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise Exception(f"Request failed after {self.max_retries} attempts: {str(e)}")
                
                # Wait before retry
                time.sleep(0.5 * (attempt + 1))
                
        except Exception as e:
            logger.error(f"Error generating boss action: {str(e)}")
            # Return a fallback action
            return self._create_fallback_action(player_context, boss_health, battle_phase)
    
    async def generate_boss_action_async(self, prompt_engine_id: str, player_context: PlayerContextData,
                                       similar_contexts: List[Dict[str, Any]], boss_health: float,
                                       battle_phase: str, environment: str = "standard arena",
                                       realtime_factors: Dict[str, Any] = None) -> BossActionResponse:
        """Generate a boss action using the prompt engine (async version)"""
        try:
            session = await self._get_session()
            
            # Format inputs
            player_context_text = self._format_player_context(player_context)
            similar_contexts_text = self._format_similar_contexts(similar_contexts)
            realtime_factors_text = self._format_realtime_factors(realtime_factors or {})
            
            input_values = {
                "player_context": player_context_text,
                "similar_contexts": similar_contexts_text,
                "boss_health": str(int(boss_health * 100)),
                "battle_phase": battle_phase,
                "environment": environment,
                "realtime_factors": realtime_factors_text
            }
            
            # Execute with retries
            for attempt in range(self.max_retries):
                try:
                    payload = {"input_values": input_values}
                    
                    async with session.post(
                        f"{self.base_url}/prompt_engine/{prompt_engine_id}",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            boss_action_data = result.get("result", {})
                            
                            boss_action = self._parse_boss_action_response(boss_action_data)
                            logger.info(f"Generated boss action async: {boss_action.boss_action}")
                            return boss_action
                        else:
                            error_text = await response.text()
                            logger.warning(f"Async attempt {attempt + 1} failed: {response.status} - {error_text}")
                            if attempt == self.max_retries - 1:
                                raise Exception(f"Failed after {self.max_retries} attempts: {error_text}")
                
                except asyncio.TimeoutError:
                    logger.warning(f"Async timeout on attempt {attempt + 1}")
                    if attempt == self.max_retries - 1:
                        raise Exception("Async request timed out after multiple attempts")
                
                except Exception as e:
                    logger.warning(f"Async error on attempt {attempt + 1}: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise Exception(f"Async request failed after {self.max_retries} attempts: {str(e)}")
                
                # Wait before retry
                await asyncio.sleep(0.5 * (attempt + 1))
        
        except Exception as e:
            logger.error(f"Error in async boss action generation: {str(e)}")
            return self._create_fallback_action(player_context, boss_health, battle_phase)
    
    def _format_player_context(self, player_context: PlayerContextData) -> str:
        """Format player context for the prompt"""
        context_parts = [
            f"Frequent actions: {', '.join(player_context.frequent_actions)}",
            f"Dodge frequency: {player_context.dodge_frequency:.1%}",
            f"Attack patterns: {', '.join(player_context.attack_patterns)}",
            f"Movement style: {player_context.movement_style}",
            f"Reaction time: {player_context.reaction_time:.2f}s",
            f"Current health: {player_context.health_percentage:.1%}",
            f"Difficulty preference: {player_context.difficulty_preference}",
            f"Session duration: {player_context.session_duration:.1f} minutes",
            f"Recent deaths: {player_context.recent_deaths}",
            f"Equipment level: {player_context.equipment_level}"
        ]
        
        if player_context.additional_context:
            for key, value in player_context.additional_context.items():
                context_parts.append(f"{key}: {value}")
        
        return " | ".join(context_parts)
    
    def _format_similar_contexts(self, similar_contexts: List[Dict[str, Any]]) -> str:
        """Format similar contexts for the prompt"""
        if not similar_contexts:
            return "No similar past situations found."
        
        formatted_contexts = []
        for i, context in enumerate(similar_contexts[:3], 1):  # Limit to top 3
            effectiveness = context.get('effectiveness_score', 0.0)
            similarity = context.get('similarity_score', 0.0)
            context_data = context.get('context_data', {})
            
            context_summary = f"Situation {i} (Effectiveness: {effectiveness:.1%}, Similarity: {similarity:.1%}): "
            context_summary += f"Player had {context_data.get('dodge_frequency', 0):.1%} dodge rate, "
            context_summary += f"{context_data.get('health_percentage', 1):.1%} health, "
            context_summary += f"preferred {context_data.get('difficulty_preference', 'normal')} difficulty. "
            context_summary += f"Action was {'very effective' if effectiveness > 0.8 else 'effective' if effectiveness > 0.5 else 'moderately effective'}."
            
            formatted_contexts.append(context_summary)
        
        return " | ".join(formatted_contexts)
    
    def _format_realtime_factors(self, realtime_factors: Dict[str, Any]) -> str:
        """Format real-time factors for the prompt"""
        if not realtime_factors:
            return "Normal battle conditions"
        
        factors = []
        for key, value in realtime_factors.items():
            factors.append(f"{key}: {value}")
        
        return " | ".join(factors)
    
    def _parse_boss_action_response(self, response_data: Dict[str, Any]) -> BossActionResponse:
        """Parse and validate the boss action response"""
        try:
            # Extract required fields with defaults
            boss_action = response_data.get("boss_action", "basic attack")
            action_type = response_data.get("action_type", "attack")
            intensity = float(response_data.get("intensity", 0.5))
            
            # Ensure intensity is within bounds
            intensity = max(0.0, min(1.0, intensity))
            
            # Extract optional fields
            target_area = response_data.get("target_area")
            duration = response_data.get("duration")
            cooldown = response_data.get("cooldown")
            animation_id = response_data.get("animation_id")
            sound_effects = response_data.get("sound_effects", [])
            visual_effects = response_data.get("visual_effects", [])
            damage_multiplier = response_data.get("damage_multiplier", 1.0)
            success_probability = response_data.get("success_probability")
            confidence_level = response_data.get("confidence_level")
            adaptation_reason = response_data.get("adaptation_reason")
            counter_strategy = response_data.get("counter_strategy")
            reasoning = response_data.get("reasoning")
            
            # Convert to appropriate types
            if duration is not None:
                duration = float(duration)
            if cooldown is not None:
                cooldown = float(cooldown)
            if damage_multiplier is not None:
                damage_multiplier = float(damage_multiplier)
            if success_probability is not None:
                success_probability = float(success_probability)
            if confidence_level is not None:
                confidence_level = float(confidence_level)
            
            # Combine reasoning fields
            full_reasoning = []
            if reasoning:
                full_reasoning.append(f"Decision: {reasoning}")
            if adaptation_reason:
                full_reasoning.append(f"Adaptation: {adaptation_reason}")
            if counter_strategy:
                full_reasoning.append(f"Counter-strategy: {counter_strategy}")
            
            combined_reasoning = " | ".join(full_reasoning) if full_reasoning else None
            
            return BossActionResponse(
                boss_action=boss_action,
                action_type=action_type,
                intensity=intensity,
                target_area=target_area,
                duration=duration,
                cooldown=cooldown,
                animation_id=animation_id,
                sound_effects=sound_effects if isinstance(sound_effects, list) else [],
                visual_effects=visual_effects if isinstance(visual_effects, list) else [],
                damage_multiplier=damage_multiplier,
                success_probability=success_probability,
                reasoning=combined_reasoning
            )
            
        except Exception as e:
            logger.error(f"Error parsing boss action response: {str(e)}")
            # Return a default action if parsing fails
            return self._create_fallback_action(None, 1.0, "unknown")
    
    def _create_fallback_action(self, player_context: Optional[PlayerContextData], 
                              boss_health: float, battle_phase: str) -> BossActionResponse:
        """Create a fallback action when API fails"""
        # Simple fallback logic based on available information
        if player_context and player_context.dodge_frequency > 0.7:
            action = "area_attack"
            intensity = 0.6
        elif boss_health < 0.3:
            action = "desperate_strike"
            intensity = 0.8
        else:
            action = "basic_attack"
            intensity = 0.5
        
        return BossActionResponse(
            boss_action=action,
            action_type="attack",
            intensity=intensity,
            reasoning="Fallback action due to API unavailability"
        )
    
    async def get_prompt_details_async(self, prompt_engine_id: str) -> Dict[str, Any]:
        """Get details of a prompt (async version)"""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/prompt_engine/{prompt_engine_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get prompt details: {response.status}")
                    return {}
        
        except Exception as e:
            logger.error(f"Error getting prompt details: {str(e)}")
            return {}
    
    async def delete_prompt_async(self, prompt_engine_id: str) -> bool:
        """Delete a prompt (async version)"""
        try:
            session = await self._get_session()
            
            async with session.delete(f"{self.base_url}/prompt_engine/{prompt_engine_id}") as response:
                if response.status == 200:
                    logger.info(f"Deleted prompt: {prompt_engine_id}")
                    return True
                else:
                    logger.error(f"Failed to delete prompt: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Error deleting prompt: {str(e)}")
            return False