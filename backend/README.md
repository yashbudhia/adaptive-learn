# Adaptive Boss Behavior System

An intelligent boss behavior system that uses a RAG (Retrieval-Augmented Generation) pipeline combining FAISS vector search, OpenAI embeddings, and JigsawStack Prompt Engine to create adaptive, learning boss AI for games.

## 🎯 Features

- **RAG Pipeline**: Combines FAISS vector search with OpenAI embeddings for context retrieval
- **JigsawStack Integration**: Uses JigsawStack Prompt Engine for game-specific AI responses
- **Adaptive Learning**: Learns from action outcomes to improve future boss behaviors
- **Multi-Game Support**: Handles different games with unique vocabularies and mechanics
- **Secure API**: JWT-based authentication with encrypted credential storage
- **Real-time Analytics**: Provides insights into system performance and learning progress
- **Scalable Architecture**: Built with FastAPI, PostgreSQL, and Redis for production use

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Game Client   │───▶│   FastAPI API    │───▶│  JigsawStack    │
└─────────────────┘    └──────────────────┘    │ Prompt Engine   │
                                │               └─────────────────┘
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Boss Service   │───▶│ OpenAI Embeddings│
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ FAISS Vector DB  │    │   PostgreSQL    │
                       │   (Similarity)   │    │   (Metadata)    │
                       └──────────────────┘    └─────────────────┘
```

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

The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

## 📖 Usage

### 1. Register Your Game

First, register your game with its specific vocabulary and mechanics:

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

# Save the access token for future requests
access_token = response.json()["access_token"]
```

### 2. Generate Boss Actions

Request adaptive boss actions based on player context:

```python
player_context = {
    "frequent_actions": ["dodge", "attack"],
    "dodge_frequency": 0.8,
    "attack_patterns": ["combo_attack"],
    "movement_style": "defensive",
    "reaction_time": 0.4,
    "health_percentage": 0.7,
    "difficulty_preference": "normal",
    "session_duration": 10.0,
    "recent_deaths": 1,
    "equipment_level": 3
}

request_data = {
    "game_id": "my_game_001",
    "player_context": player_context,
    "boss_health_percentage": 0.8,
    "battle_phase": "opening",
    "environment_factors": {"environment": "arena"}
}

response = requests.post(
    "http://localhost:8000/api/v1/boss/action",
    json=request_data,
    headers={"Authorization": f"Bearer {access_token}"}
)

boss_action = response.json()
print(f"Boss Action: {boss_action['boss_action']}")
print(f"Intensity: {boss_action['intensity']}")
```

### 3. Log Action Outcomes

Help the system learn by logging the effectiveness of boss actions:

```python
outcome_data = {
    "action_id": 123,  # ID from your database
    "outcome": "success",
    "effectiveness_score": 0.85,
    "damage_dealt": 30.0,
    "player_hit": True,
    "execution_time": 1.5
}

response = requests.post(
    "http://localhost:8000/api/v1/boss/action/outcome",
    json=outcome_data,
    headers={"Authorization": f"Bearer {access_token}"}
)
```

### 4. Monitor Performance

Get insights into your game's adaptive AI performance:

```python
response = requests.get(
    f"http://localhost:8000/api/v1/games/{game_id}/stats",
    headers={"Authorization": f"Bearer {access_token}"}
)

stats = response.json()
print(f"Success Rate: {stats['success_rate']:.2%}")
print(f"Learning Progress: {stats['learning_progress']}")
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

### Game Vocabulary

When registering a game, provide a comprehensive vocabulary:

```json
{
  "boss_actions": ["list of possible boss actions"],
  "action_types": ["attack", "defend", "special", "magic"],
  "environments": ["different battle environments"],
  "difficulty_levels": ["easy", "normal", "hard"],
  "damage_types": ["physical", "magical", "elemental"],
  "status_effects": ["poison", "stun", "slow"]
}
```

## 🔒 Security

- **JWT Authentication**: All game-specific endpoints require valid JWT tokens
- **Encrypted Storage**: Sensitive data is encrypted using Fernet encryption
- **Rate Limiting**: Built-in protection against abuse (configure as needed)
- **Input Validation**: Comprehensive request validation using Pydantic

## 📊 How It Works

1. **Context Analysis**: Player behavior is converted to embeddings using OpenAI
2. **Similarity Search**: FAISS finds similar past situations and their outcomes
3. **Prompt Generation**: JigsawStack generates contextual boss actions
4. **Learning Loop**: Action outcomes are stored and used to improve future decisions
5. **Adaptation**: The system continuously learns what works best for each situation

## 🎮 Example Integration

See `examples/example_game_registration.py` for a complete example of:
- Game registration
- Boss action generation
- Outcome logging
- Performance monitoring

## 🚀 Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "-m", "app.main"]
```

### Environment Setup

- Use environment-specific `.env` files
- Configure proper CORS origins
- Set up SSL/TLS certificates
- Configure database connection pooling
- Set up monitoring and logging

## 📈 Performance Optimization

- **Caching**: Redis caching for frequently requested actions
- **Batch Processing**: Efficient embedding generation
- **Index Optimization**: Automatic FAISS index cleanup
- **Background Tasks**: Non-blocking outcome processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint for API documentation
- **Issues**: Report bugs and feature requests on GitHub
- **Discord**: Join our community for discussions

## 🔮 Roadmap

- [ ] Multi-model support (different LLM providers)
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] Real-time adaptation during gameplay
- [ ] Integration with popular game engines
- [ ] Machine learning model fine-tuning

---

Built with ❤️ for the gaming community. Create smarter, more engaging boss encounters that adapt to your players!