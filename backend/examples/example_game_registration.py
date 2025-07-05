"""
Example script showing how to register a game with the Adaptive Boss Behavior System
"""

import requests
import json

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

def register_game():
    """Register a sample game with the system"""
    
    # Sample game configuration
    game_data = {
        "game_id": "fantasy_rpg_001",
        "name": "Fantasy RPG Demo",
        "description": "A fantasy RPG with adaptive boss encounters",
        "vocabulary": {
            "game_name": "Fantasy RPG Demo",
            "boss_actions": [
                "sword_slash",
                "fire_breath",
                "ground_slam",
                "magic_missile",
                "defensive_stance",
                "rage_mode",
                "teleport_strike",
                "area_of_effect_spell",
                "healing_potion",
                "summon_minions"
            ],
            "action_types": [
                "attack",
                "defend",
                "special",
                "magic",
                "movement",
                "buff",
                "debuff"
            ],
            "environments": [
                "castle_throne_room",
                "dark_forest",
                "volcanic_cave",
                "ice_temple",
                "standard_arena"
            ],
            "difficulty_levels": [
                "easy",
                "normal",
                "hard",
                "nightmare"
            ],
            "damage_types": [
                "physical",
                "fire",
                "ice",
                "lightning",
                "dark",
                "holy"
            ],
            "status_effects": [
                "poison",
                "burn",
                "freeze",
                "stun",
                "slow",
                "haste",
                "shield"
            ]
        }
    }
    
    try:
        # Register the game
        response = requests.post(
            f"{API_BASE_URL}/games/register",
            json=game_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Game registered successfully!")
            print(f"Game ID: {result['game_id']}")
            print(f"Prompt Engine ID: {result.get('prompt_engine_id', 'N/A')}")
            print(f"Access Token: {result.get('access_token', 'N/A')}")
            
            # Save the access token for future use
            with open("game_token.txt", "w") as f:
                f.write(result.get('access_token', ''))
            print("💾 Access token saved to game_token.txt")
            
            return result
        else:
            print(f"❌ Failed to register game: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error registering game: {str(e)}")
        return None


def test_boss_action():
    """Test boss action generation"""
    
    # Load access token
    try:
        with open("game_token.txt", "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print("❌ No access token found. Please register the game first.")
        return
    
    # Sample player context
    player_context = {
        "frequent_actions": ["dodge", "attack", "block"],
        "dodge_frequency": 0.7,
        "attack_patterns": ["combo_attack", "hit_and_run"],
        "movement_style": "aggressive",
        "reaction_time": 0.3,
        "health_percentage": 0.8,
        "difficulty_preference": "normal",
        "session_duration": 15.5,
        "recent_deaths": 2,
        "equipment_level": 5,
        "additional_context": {
            "preferred_weapon": "sword",
            "magic_usage": "low",
            "exploration_style": "thorough"
        }
    }
    
    # Boss action request
    request_data = {
        "game_id": "fantasy_rpg_001",
        "player_context": player_context,
        "boss_health_percentage": 0.6,
        "battle_phase": "mid_battle",
        "environment_factors": {
            "environment": "castle_throne_room",
            "lighting": "dim",
            "obstacles": ["pillars", "throne"]
        }
    }
    
    try:
        # Generate boss action
        response = requests.post(
            f"{API_BASE_URL}/boss/action",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Boss action generated successfully!")
            print(f"Action: {result['boss_action']}")
            print(f"Type: {result['action_type']}")
            print(f"Intensity: {result['intensity']}")
            print(f"Reasoning: {result.get('reasoning', 'N/A')}")
            
            # Pretty print the full response
            print("\n📋 Full Response:")
            print(json.dumps(result, indent=2))
            
            return result
        else:
            print(f"❌ Failed to generate boss action: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating boss action: {str(e)}")
        return None


def log_action_outcome(action_id: int):
    """Log the outcome of a boss action"""
    
    # Load access token
    try:
        with open("game_token.txt", "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print("❌ No access token found. Please register the game first.")
        return
    
    # Sample outcome data
    outcome_data = {
        "action_id": action_id,
        "outcome": "success",
        "effectiveness_score": 0.8,
        "damage_dealt": 25.0,
        "player_hit": True,
        "execution_time": 1.2,
        "player_reaction": "dodged_partially",
        "additional_metrics": {
            "player_health_after": 0.6,
            "boss_position_advantage": True,
            "environmental_factor_used": True
        }
    }
    
    try:
        # Log the outcome
        response = requests.post(
            f"{API_BASE_URL}/boss/action/outcome",
            json=outcome_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Action outcome logged successfully!")
            print(f"Message: {result['message']}")
            return result
        else:
            print(f"❌ Failed to log action outcome: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error logging action outcome: {str(e)}")
        return None


def get_game_stats():
    """Get game statistics"""
    
    # Load access token
    try:
        with open("game_token.txt", "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        print("❌ No access token found. Please register the game first.")
        return
    
    try:
        # Get game stats
        response = requests.get(
            f"{API_BASE_URL}/games/fantasy_rpg_001/stats",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Game statistics retrieved successfully!")
            print(f"Total Contexts: {result['total_contexts']}")
            print(f"Total Actions: {result['total_actions']}")
            print(f"Average Effectiveness: {result['avg_effectiveness']:.2%}")
            print(f"Success Rate: {result['success_rate']:.2%}")
            print(f"Recent Effectiveness: {result['recent_effectiveness']:.2%}")
            
            # Pretty print the full response
            print("\n📊 Full Statistics:")
            print(json.dumps(result, indent=2))
            
            return result
        else:
            print(f"❌ Failed to get game stats: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting game stats: {str(e)}")
        return None


if __name__ == "__main__":
    print("🎮 Adaptive Boss Behavior System - Example Usage")
    print("=" * 50)
    
    # Step 1: Register the game
    print("\n1️⃣ Registering game...")
    game_result = register_game()
    
    if game_result:
        # Step 2: Test boss action generation
        print("\n2️⃣ Testing boss action generation...")
        action_result = test_boss_action()
        
        if action_result:
            # Step 3: Log action outcome (using a dummy action ID)
            print("\n3️⃣ Logging action outcome...")
            log_action_outcome(1)  # In real usage, you'd get this from the database
            
            # Step 4: Get game statistics
            print("\n4️⃣ Getting game statistics...")
            get_game_stats()
    
    print("\n✨ Example completed!")
    print("Check the API documentation at http://localhost:8000/docs for more details.")