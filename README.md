# Adaptive Boss Behavior System with Real-time WebSocket Support

An intelligent boss behavior system that uses a RAG (Retrieval-Augmented Generation) pipeline combining FAISS vector search, OpenAI embeddings, and JigsawStack Prompt Engine to create adaptive, learning boss AI for games. **Now with real-time WebSocket support for instant boss action generation and learning updates!**

## 🚀 New Real-time Features

- **WebSocket Integration**: Real-time boss action generation and learning updates
- **Instant Response**: Sub-second boss action generation via WebSocket connections
- **Live Learning**: Real-time feedback and system improvement notifications
- **Connection Management**: Automatic reconnection and heartbeat monitoring
- **Multi-client Support**: Handle multiple game clients simultaneously

## 🎯 Features

- **Real-time WebSocket Communication**: Instant boss actions and learning updates
- **RAG Pipeline**: Combines FAISS vector search with OpenAI embeddings for context retrieval
- **JigsawStack Integration**: Uses JigsawStack Prompt Engine for game-specific AI responses
- **Adaptive Learning**: Learns from action outcomes to improve future boss behaviors
- **Multi-Game Support**: Handles different games with unique vocabularies and mechanics
- **Secure API**: JWT-based authentication with encrypted credential storage
- **Real-time Analytics**: Live insights into system performance and learning progress
- **Scalable Architecture**: Built with FastAPI, PostgreSQL, Redis, and WebSockets for production use

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Game Client   │◄──►│   WebSocket API  │───▶│  JigsawStack    │
│  (Unity/Web)    │    │   (Real-time)    │    │ Prompt Engine   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Boss Service   │───▶│ OpenAI Embeddings│
                       │   (Adaptive)     │    │   (Context)     │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ FAISS Vector DB  │    │   PostgreSQL    │
                       │   (Similarity)   │    │   (Metadata)    │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │      Redis       │
                       │   (Real-time)    │
                       └──────────────────┘
```

## 🔌 WebSocket Integration

### Connection URL
```
ws://localhost:8000/api/v1/ws/{game_id}?token={jwt_token}&session_id={optional_session_id}
```

### Message Types
- `boss_action_request`: Request adaptive boss action
- `boss_action_response`: Receive generated boss action
- `action_outcome`: Log action effectiveness for learning
- `learning_update`: Receive system learning notifications
- `heartbeat`: Connection health monitoring
- `error`: Error notifications
- `status`: Processing status updates

### Real-time Workflow
1. **Connect**: Establish WebSocket connection with JWT token
2. **Request**: Send player context for boss action generation
3. **Receive**: Get adaptive boss action in real-time (< 2 seconds)
4. **Execute**: Perform boss action in your game
5. **Feedback**: Send action outcome for system learning
6. **Learn**: Receive learning updates and improvements

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- OpenAI API Key
- JigsawStack API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd adaptive-learn
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database configuration
   ```

4. **Set up the database**
   ```bash
   # Create PostgreSQL database
   createdb adaptive_boss_db
   
   # The application will automatically create tables on startup
   ```

5. **Start Redis**
   ```bash
   redis-server
   ```

6. **Run the application**
   ```bash
   python -m app.main
   ```

The API will be available at `http://localhost:8000` with WebSocket endpoint at `ws://localhost:8000/api/v1/ws/{game_id}`.

## 🎮 Usage Examples

### 1. Register Your Game

```python
import requests

game_data = {
    "game_id": "my_game_001",
    "name": "My Awesome Game",
    "description": "A game with adaptive boss AI",
    "vocabulary": {
        "boss_actions": ["attack", "defend", "special_move"],
        "action_types": ["aggressive", "defensive", "tactical"],
        "environments": ["arena", "forest", "cave"],
        "difficulty_levels": ["easy", "normal", "hard"]
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/games/register",
    json=game_data
)

access_token = response.json()["access_token"]
```

### 2. WebSocket Connection (Python)

```python
import asyncio
import websockets
import json

async def connect_websocket():
    uri = f"ws://localhost:8000/api/v1/ws/my_game_001?token={access_token}"
    
    async with websockets.connect(uri) as websocket:
        # Send boss action request
        request = {
            "type": "boss_action_request",
            "data": {
                "player_context": {
                    "frequent_actions": ["dodge", "attack"],
                    "dodge_frequency": 0.7,
                    "attack_patterns": ["combo_attack"],
                    "movement_style": "aggressive",
                    "reaction_time": 0.3,
                    "health_percentage": 0.8,
                    "difficulty_preference": "normal",
                    "session_duration": 10.0,
                    "recent_deaths": 1,
                    "equipment_level": 5
                },
                "boss_health_percentage": 0.8,
                "battle_phase": "mid_battle",
                "environment_factors": {"environment": "arena"}
            }
        }
        
        await websocket.send(json.dumps(request))
        
        # Receive boss action response
        response = await websocket.recv()
        boss_action = json.loads(response)
        
        print(f"Boss Action: {boss_action['data']['boss_action']['boss_action']}")
```

### 3. Unity Integration

```csharp
// Use the provided Unity WebSocket example
var bossManager = GetComponent<RealtimeAdaptiveBossManager>();
bossManager.gameId = "my_game_001";
bossManager.accessToken = "your_jwt_token";

// Request boss action
bossManager.RequestBossAction();

// Handle boss action response
bossManager.OnBossActionReceived += (bossAction) => {
    Debug.Log($"Execute: {bossAction.bossAction}");
    // Execute the boss action in your game
};
```

### 4. Log Action Outcomes

```python
# After executing the boss action, log its effectiveness
outcome_message = {
    "type": "action_outcome",
    "data": {
        "action_id": 123,
        "outcome": "success",
        "effectiveness_score": 0.85,
        "damage_dealt": 30.0,
        "player_hit": True,
        "execution_time": 1.5
    }
}

await websocket.send(json.dumps(outcome_message))
```

## 📊 Real-time Monitoring

### Get Live Statistics
```bash
curl http://localhost:8000/api/v1/games/my_game_001/realtime-stats
```

### WebSocket Connection Info
```bash
curl http://localhost:8000/websocket-info
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | Yes |
| `JIGSAWSTACK_API_KEY` | JigsawStack API key for prompt engine | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | No |
| `SECRET_KEY` | JWT secret key | Yes |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | WebSocket heartbeat interval (seconds) | No |
| `WEBSOCKET_TIMEOUT` | WebSocket connection timeout (seconds) | No |
| `MAX_WEBSOCKET_CONNECTIONS` | Maximum concurrent WebSocket connections | No |

### WebSocket Settings

```python
# Real-time configuration
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # seconds
WEBSOCKET_TIMEOUT = 300  # 5 minutes
MAX_WEBSOCKET_CONNECTIONS = 1000
REALTIME_ACTION_TIMEOUT = 10  # seconds
REALTIME_UPDATE_INTERVAL = 0.1  # seconds
```

## 🎮 Integration Examples

The system includes comprehensive integration examples for:

- **Python WebSocket Client**: `examples/websocket_client_example.py`
- **Unity Real-time Integration**: `examples/unity_websocket_example.cs`
- **JavaScript/Web**: `examples/javascript_integration_example.js`
- **Standard REST API**: `examples/example_game_registration.py`

## 🔒 Security

### WebSocket Authentication
- JWT tokens required for WebSocket connections
- Token validation on connection and message handling
- Automatic session management and cleanup
- Rate limiting and connection limits

### API Security
- JWT-based authentication for all endpoints
- Encrypted credential storage using Fernet encryption
- Input validation using Pydantic models
- CORS and trusted host middleware

## 📈 Performance

### Real-time Metrics
- **Response Time**: < 2 seconds for boss action generation
- **Throughput**: 1000+ concurrent WebSocket connections
- **Learning Speed**: Real-time context updates and improvements
- **Cache Hit Rate**: 75%+ for frequently requested contexts

### Optimization Features
- Redis caching for fast lookups
- FAISS index optimization
- Background task processing
- Connection pooling and management

## 🚀 Production Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Environment Setup
- Use environment-specific `.env` files
- Configure proper CORS origins
- Set up SSL/TLS certificates for WebSocket security
- Configure load balancing for multiple instances
- Set up monitoring and logging

## 🔍 Troubleshooting

### Common WebSocket Issues

1. **Connection Failed**
   - Verify JWT token is valid
   - Check game_id exists in database
   - Ensure WebSocket URL is correct

2. **Messages Not Received**
   - Check WebSocket connection status
   - Verify message format matches expected schema
   - Check server logs for errors

3. **High Latency**
   - Check Redis connection
   - Monitor FAISS index performance
   - Verify OpenAI API response times

## 📚 API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **WebSocket Info**: http://localhost:8000/websocket-info
- **Health Check**: http://localhost:8000/api/v1/health

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for WebSocket functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint for API documentation
- **WebSocket Examples**: See `examples/` directory for integration samples
- **Issues**: Report bugs and feature requests on GitHub
- **Discord**: Join our community for real-time discussions

## 🔮 Roadmap

- [ ] **Multi-model Support**: Different LLM providers for boss actions
- [ ] **Advanced Analytics Dashboard**: Real-time performance visualization
- [ ] **A/B Testing Framework**: Compare different boss behavior strategies
- [ ] **Mobile SDK**: Native mobile integration libraries
- [ ] **Game Engine Plugins**: Direct integration with Unity, Unreal, Godot
- [ ] **Machine Learning Pipeline**: Custom model training on game data
- [ ] **Cluster Support**: Distributed WebSocket handling

---

🎮 **Real-time Adaptive Boss AI** - Create smarter, more engaging boss encounters that adapt to your players in real-time!