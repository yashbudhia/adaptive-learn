"""
Real-time WebSocket client example for the Adaptive Boss Behavior System
"""

import asyncio
import websockets
import json
import time
from typing import Dict, Any, Optional

class AdaptiveBossWebSocketClient:
    """WebSocket client for real-time adaptive boss behavior"""
    
    def __init__(self, base_url: str = "ws://localhost:8000/api/v1"):
        self.base_url = base_url
        self.websocket = None
        self.game_id = None
        self.access_token = None
        self.session_id = None
        self.is_connected = False
        self.message_handlers = {}
        
        # Set up default message handlers
        self.message_handlers.update({
            "connect": self._handle_connect,
            "boss_action_response": self._handle_boss_action_response,
            "learning_update": self._handle_learning_update,
            "heartbeat": self._handle_heartbeat,
            "error": self._handle_error,
            "status": self._handle_status
        })
    
    async def connect(self, game_id: str, access_token: str, session_id: Optional[str] = None):
        """Connect to the WebSocket endpoint"""
        self.game_id = game_id
        self.access_token = access_token
        self.session_id = session_id or f"client_{int(time.time())}"
        
        # Build WebSocket URL
        url = f"{self.base_url}/ws/{game_id}?token={access_token}"
        if session_id:
            url += f"&session_id={session_id}"
        
        try:
            print(f"🔌 Connecting to {url}")
            self.websocket = await websockets.connect(url)
            self.is_connected = True
            print(f"✅ Connected to WebSocket for game {game_id}")
            
            # Start message handling loop
            await self._message_loop()
            
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket and self.is_connected:
            await self.websocket.close()
            self.is_connected = False
            print("👋 Disconnected from WebSocket")
    
    async def send_message(self, message_type: str, data: Dict[str, Any]):
        """Send a message to the server"""
        if not self.is_connected or not self.websocket:
            raise Exception("Not connected to WebSocket")
        
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time(),
            "session_id": self.session_id,
            "game_id": self.game_id
        }
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Sent {message_type} message")
        except Exception as e:
            print(f"❌ Failed to send message: {str(e)}")
            raise
    
    async def request_boss_action(self, player_context: Dict[str, Any], 
                                boss_health: float, battle_phase: str,
                                environment_factors: Dict[str, Any] = None,
                                request_id: str = None):
        """Request a boss action in real-time"""
        data = {
            "player_context": player_context,
            "boss_health_percentage": boss_health,
            "battle_phase": battle_phase,
            "environment_factors": environment_factors or {},
            "request_id": request_id or f"req_{int(time.time())}"
        }
        
        await self.send_message("boss_action_request", data)
    
    async def log_action_outcome(self, action_id: int, outcome: str, 
                               effectiveness_score: float, damage_dealt: float,
                               player_hit: bool, execution_time: float,
                               additional_metrics: Dict[str, Any] = None):
        """Log the outcome of a boss action"""
        data = {
            "action_id": action_id,
            "outcome": outcome,
            "effectiveness_score": effectiveness_score,
            "damage_dealt": damage_dealt,
            "player_hit": player_hit,
            "execution_time": execution_time,
            "additional_metrics": additional_metrics or {}
        }
        
        await self.send_message("action_outcome", data)
    
    async def send_heartbeat(self):
        """Send heartbeat to maintain connection"""
        await self.send_message("heartbeat", {})
    
    async def _message_loop(self):
        """Main message handling loop"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type")
                    message_data = data.get("data", {})
                    
                    print(f"📥 Received {message_type} message")
                    
                    # Handle message
                    if message_type in self.message_handlers:
                        await self.message_handlers[message_type](message_data)
                    else:
                        print(f"⚠️  Unknown message type: {message_type}")
                
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON received: {str(e)}")
                except Exception as e:
                    print(f"❌ Error handling message: {str(e)}")
        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            print(f"❌ Message loop error: {str(e)}")
            self.is_connected = False
    
    # Message handlers
    async def _handle_connect(self, data: Dict[str, Any]):
        """Handle connection confirmation"""
        print(f"🎉 Connection confirmed: {data.get('status')}")
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Features: {', '.join(data.get('features', []))}")
    
    async def _handle_boss_action_response(self, data: Dict[str, Any]):
        """Handle boss action response"""
        boss_action = data.get("boss_action", {})
        request_id = data.get("request_id")
        
        print(f"🎯 Boss Action Received (Request: {request_id}):")
        print(f"   Action: {boss_action.get('boss_action')}")
        print(f"   Type: {boss_action.get('action_type')}")
        print(f"   Intensity: {boss_action.get('intensity'):.2f}")
        print(f"   Response Time: {boss_action.get('response_time', 0):.3f}s")
        
        if boss_action.get('reasoning'):
            print(f"   Reasoning: {boss_action.get('reasoning')}")
        
        # Here you would execute the boss action in your game
        await self._simulate_boss_action_execution(boss_action, request_id)
    
    async def _handle_learning_update(self, data: Dict[str, Any]):
        """Handle learning update"""
        print(f"🧠 Learning Update:")
        print(f"   Contexts Learned: {data.get('contexts_learned', 0)}")
        print(f"   Avg Effectiveness: {data.get('avg_effectiveness', 0):.1%}")
        print(f"   Performance Trend: {data.get('performance_trend', 'unknown')}")
        
        improvements = data.get('recent_improvements', [])
        if improvements:
            print(f"   Recent Improvements: {', '.join(improvements)}")
    
    async def _handle_heartbeat(self, data: Dict[str, Any]):
        """Handle heartbeat"""
        if data.get('status') == 'ping':
            # Respond to server ping
            await self.send_message("heartbeat", {"status": "pong"})
    
    async def _handle_error(self, data: Dict[str, Any]):
        """Handle error message"""
        print(f"❌ Server Error: {data.get('error', 'Unknown error')}")
    
    async def _handle_status(self, data: Dict[str, Any]):
        """Handle status message"""
        status = data.get('status')
        if status == 'processing':
            print(f"⏳ Server processing request: {data.get('request_id')}")
            print(f"   Estimated time: {data.get('estimated_time', 0)}s")
    
    async def _simulate_boss_action_execution(self, boss_action: Dict[str, Any], request_id: str):
        """Simulate executing the boss action and log outcome"""
        print(f"🎮 Executing boss action: {boss_action.get('boss_action')}")
        
        # Simulate action execution
        await asyncio.sleep(1.0)  # Simulate execution time
        
        # Simulate outcome
        success = boss_action.get('intensity', 0.5) > 0.3  # Simple success logic
        effectiveness = min(boss_action.get('intensity', 0.5) + 0.2, 1.0) if success else 0.2
        damage = boss_action.get('intensity', 0.5) * 30 if success else 0
        player_hit = success and boss_action.get('intensity', 0.5) > 0.4
        
        print(f"   Result: {'Success' if success else 'Failed'}")
        print(f"   Effectiveness: {effectiveness:.1%}")
        print(f"   Damage: {damage:.1f}")
        print(f"   Player Hit: {player_hit}")
        
        # Log outcome (using dummy action_id for demo)
        await self.log_action_outcome(
            action_id=1,  # In real usage, you'd get this from your game database
            outcome="success" if success else "failure",
            effectiveness_score=effectiveness,
            damage_dealt=damage,
            player_hit=player_hit,
            execution_time=1.0,
            additional_metrics={
                "request_id": request_id,
                "boss_action_type": boss_action.get('action_type'),
                "player_reaction": "dodged" if not player_hit else "hit"
            }
        )


async def main():
    """Example usage of the WebSocket client"""
    print("🎮 Adaptive Boss WebSocket Client Example")
    print("=" * 50)
    
    # You would get these from registering your game
    game_id = "websocket_demo_001"
    access_token = "your_jwt_token_here"  # Get this from /api/v1/games/{game_id}/token
    
    client = AdaptiveBossWebSocketClient()
    
    try:
        # Connect to WebSocket
        print("\n1️⃣ Connecting to WebSocket...")
        await client.connect(game_id, access_token)
        
        # Wait a moment for connection to stabilize
        await asyncio.sleep(1)
        
        # Example player context
        player_context = {
            "frequent_actions": ["dodge", "attack", "block"],
            "dodge_frequency": 0.7,
            "attack_patterns": ["combo_attack", "hit_and_run"],
            "movement_style": "aggressive",
            "reaction_time": 0.3,
            "health_percentage": 0.8,
            "difficulty_preference": "normal",
            "session_duration": 15.0,
            "recent_deaths": 1,
            "equipment_level": 5,
            "additional_context": {
                "preferred_weapon": "sword",
                "magic_usage": "low"
            }
        }
        
        # Request boss actions
        print("\n2️⃣ Requesting boss actions...")
        
        for i in range(3):
            print(f"\n--- Boss Action Request {i+1} ---")
            
            await client.request_boss_action(
                player_context=player_context,
                boss_health=0.8 - (i * 0.2),  # Boss health decreases
                battle_phase=["opening", "mid_battle", "final_phase"][i],
                environment_factors={
                    "environment": "arena",
                    "lighting": "dim",
                    "obstacles": ["pillars", "throne"]
                },
                request_id=f"demo_request_{i+1}"
            )
            
            # Wait for response and processing
            await asyncio.sleep(3)
            
            # Update player context slightly
            player_context["recent_deaths"] = max(0, player_context["recent_deaths"] - 1)
            player_context["session_duration"] += 2.0
        
        print("\n3️⃣ Keeping connection alive...")
        
        # Keep connection alive for a bit to see learning updates
        for _ in range(5):
            await client.send_heartbeat()
            await asyncio.sleep(10)
    
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        await client.disconnect()
        print("\n✨ Example completed!")


if __name__ == "__main__":
    # Note: You need to have the server running and a valid token
    print("📝 Note: Make sure the server is running and you have a valid access token")
    print("   1. Start the server: python -m app.main")
    print("   2. Register a game or get a token from: GET /api/v1/games/{game_id}/token")
    print("   3. Update the access_token variable above")
    print()
    
    # Uncomment the line below to run the example
    # asyncio.run(main())