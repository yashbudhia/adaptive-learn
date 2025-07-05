import requests
import json
from typing import Dict, Any, List, Optional
import logging
from app.config import settings
from app.models import PlayerContextData, BossActionResponse

logger = logging.getLogger(__name__)


class JigsawStackService:
    """Service for interacting with JigsawStack Prompt Engine"""
    
    def __init__(self):
        self.api_key = settings.jigsawstack_api_key
        self.base_url = "https://api.jigsawstack.com/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def create_boss_behavior_prompt(self, game_id: str, game_vocabulary: Dict[str, Any]) -> str:
        """Create a game-specific boss behavior prompt template"""
        try:
            # Extract game-specific elements
            actions = game_vocabulary.get('boss_actions', [])
            action_types = game_vocabulary.get('action_types', [])
            environments = game_vocabulary.get('environments', [])
            difficulty_levels = game_vocabulary.get('difficulty_levels', [])
            
            # Build the prompt template
            prompt_template = f"""
You are an adaptive AI boss in the game "{game_vocabulary.get('game_name', 'Unknown Game')}". 
Your goal is to provide challenging but fair gameplay that adapts to the player's behavior and skill level.

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

INSTRUCTIONS:
1. Analyze the player's behavior patterns and current state
2. Consider similar past situations and their effectiveness
3. Choose an appropriate boss action that:
   - Matches the player's skill level
   - Provides appropriate challenge
   - Uses game-specific mechanics effectively
   - Considers the current battle context

4. Respond with a structured boss action that includes:
   - Primary action to execute
   - Action type and intensity
   - Timing and positioning details
   - Expected player response
   - Reasoning for the choice

Focus on creating engaging, adaptive gameplay that learns from past interactions.
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
                    "reasoning": "explanation of why this action was chosen"
                },
                "prompt_guard": [
                    "sexual_content",
                    "defamation",
                    "hate"
                ],
                "optimize_prompt": True
            }
            
            response = requests.post(
                f"{self.base_url}/prompt_engine",
                headers=self.headers,
                json=payload
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
    
    def generate_boss_action(self, prompt_engine_id: str, player_context: PlayerContextData,
                           similar_contexts: List[Dict[str, Any]], boss_health: float,
                           battle_phase: str, environment: str = "standard arena") -> BossActionResponse:
        """Generate a boss action using the prompt engine"""
        try:
            # Format player context
            player_context_text = self._format_player_context(player_context)
            
            # Format similar contexts
            similar_contexts_text = self._format_similar_contexts(similar_contexts)
            
            # Prepare input values
            input_values = {
                "player_context": player_context_text,
                "similar_contexts": similar_contexts_text,
                "boss_health": str(int(boss_health * 100)),
                "battle_phase": battle_phase,
                "environment": environment
            }
            
            # Execute the prompt
            payload = {
                "input_values": input_values
            }
            
            response = requests.post(
                f"{self.base_url}/prompt_engine/{prompt_engine_id}",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                boss_action_data = result.get("result", {})
                
                # Parse and validate the response
                boss_action = self._parse_boss_action_response(boss_action_data)
                
                logger.info(f"Generated boss action: {boss_action.boss_action}")
                return boss_action
            else:
                logger.error(f"Failed to generate boss action: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate boss action: {response.text}")
                
        except Exception as e:
            logger.error(f"Error generating boss action: {str(e)}")
            raise
    
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
            context_summary += f"preferred {context_data.get('difficulty_preference', 'normal')} difficulty"
            
            formatted_contexts.append(context_summary)
        
        return " | ".join(formatted_contexts)
    
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
            reasoning = response_data.get("reasoning")
            
            # Convert to float if needed
            if duration is not None:
                duration = float(duration)
            if cooldown is not None:
                cooldown = float(cooldown)
            if damage_multiplier is not None:
                damage_multiplier = float(damage_multiplier)
            if success_probability is not None:
                success_probability = float(success_probability)
            
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
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Error parsing boss action response: {str(e)}")
            # Return a default action if parsing fails
            return BossActionResponse(
                boss_action="basic attack",
                action_type="attack",
                intensity=0.5,
                reasoning="Default action due to parsing error"
            )
    
    def get_prompt_details(self, prompt_engine_id: str) -> Dict[str, Any]:
        """Get details of a prompt"""
        try:
            response = requests.get(
                f"{self.base_url}/prompt_engine/{prompt_engine_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get prompt details: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting prompt details: {str(e)}")
            return {}
    
    def delete_prompt(self, prompt_engine_id: str) -> bool:
        """Delete a prompt"""
        try:
            response = requests.delete(
                f"{self.base_url}/prompt_engine/{prompt_engine_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                logger.info(f"Deleted prompt: {prompt_engine_id}")
                return True
            else:
                logger.error(f"Failed to delete prompt: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting prompt: {str(e)}")
            return False