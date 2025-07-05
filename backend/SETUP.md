# Setup Guide - Adaptive Boss Behavior System

This guide will help you set up and run the Adaptive Boss Behavior System on your local machine or server.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** (recommended: Python 3.9 or 3.10)
- **PostgreSQL 12+** (or use Docker)
- **Redis 6+** (or use Docker)
- **Git** (for cloning the repository)

## 🔑 API Keys Required

You'll need to obtain API keys from:

1. **OpenAI**: For embeddings generation
   - Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
   - Create a new API key
   - Make sure you have credits in your account

2. **JigsawStack**: For prompt engine functionality
   - Go to [JigsawStack Dashboard](https://jigsawstack.com/dashboard)
   - Create an account and get your API key

## 🚀 Quick Start (Recommended)

### Option 1: Using Docker (Easiest)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd adaptive-learn
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   JIGSAWSTACK_API_KEY=your_jigsawstack_api_key_here
   SECRET_KEY=your_secret_key_generate_a_strong_one
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Verify the setup**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health check: http://localhost:8000/api/v1/health

### Option 2: Manual Installation

1. **Clone and setup Python environment**
   ```bash
   git clone <repository-url>
   cd adaptive-learn
   
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**
   ```bash
   # Install PostgreSQL (varies by OS)
   # Create database
   createdb adaptive_boss_db
   
   # Or use Docker:
   docker run --name postgres -e POSTGRES_DB=adaptive_boss_db -e POSTGRES_USER=adaptive_user -e POSTGRES_PASSWORD=adaptive_password -p 5432:5432 -d postgres:15-alpine
   ```

3. **Set up Redis**
   ```bash
   # Install Redis (varies by OS)
   # Start Redis server
   redis-server
   
   # Or use Docker:
   docker run --name redis -p 6379:6379 -d redis:7-alpine
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   # API Keys
   OPENAI_API_KEY=your_openai_api_key_here
   JIGSAWSTACK_API_KEY=your_jigsawstack_api_key_here
   
   # Database
   DATABASE_URL=postgresql://adaptive_user:adaptive_password@localhost:5432/adaptive_boss_db
   
   # Redis
   REDIS_URL=redis://localhost:6379/0
   
   # Security
   SECRET_KEY=your_secret_key_generate_a_strong_one
   
   # API Configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   DEBUG=True
   ```

5. **Initialize the system**
   ```bash
   # Initialize database
   python scripts/init_db.py
   
   # Test the system (optional)
   python scripts/test_system.py
   
   # Start the application
   python start.py
   ```

## 🧪 Testing the Installation

### 1. Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### 2. Run the Example
```bash
cd examples
python example_game_registration.py
```

### 3. Check the API Documentation
Visit http://localhost:8000/docs in your browser to see the interactive API documentation.

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings | - | Yes |
| `JIGSAWSTACK_API_KEY` | JigsawStack API key | - | Yes |
| `DATABASE_URL` | PostgreSQL connection string | - | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` | No |
| `SECRET_KEY` | JWT secret key | - | Yes |
| `API_HOST` | API host address | `0.0.0.0` | No |
| `API_PORT` | API port number | `8000` | No |
| `DEBUG` | Enable debug mode | `False` | No |
| `FAISS_INDEX_PATH` | Path for FAISS indexes | `./data/faiss_indexes/` | No |
| `EMBEDDING_DIMENSION` | OpenAI embedding dimension | `1536` | No |

### Generating a Secret Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

## 🎮 Integration Examples

The system includes integration examples for:

- **Unity (C#)**: `examples/unity_integration_example.cs`
- **JavaScript/Web**: `examples/javascript_integration_example.js`
- **Python**: `examples/example_game_registration.py`

## 🔍 Troubleshooting

### Common Issues

1. **"Database connection failed"**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env
   - Verify database exists

2. **"Redis connection failed"**
   - Ensure Redis is running
   - Check REDIS_URL in .env

3. **"OpenAI API error"**
   - Verify OPENAI_API_KEY is correct
   - Check your OpenAI account has credits
   - Ensure you have access to the embeddings API

4. **"JigsawStack API error"**
   - Verify JIGSAWSTACK_API_KEY is correct
   - Check your JigsawStack account status

5. **"Import errors"**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt` again

### Debug Mode

Enable debug mode for more detailed logging:
```env
DEBUG=True
```

### Logs

Check application logs for detailed error information:
- Console output when running directly
- Docker logs: `docker-compose logs api`

## 📊 Monitoring

### Health Endpoints

- **System Health**: `GET /api/v1/health`
- **Game Stats**: `GET /api/v1/games/{game_id}/stats`

### Performance Metrics

The system tracks:
- Response times
- Success rates
- Learning effectiveness
- Cache hit rates

## 🔒 Security Considerations

### Production Deployment

1. **Change default credentials**
2. **Use strong SECRET_KEY**
3. **Configure CORS properly**
4. **Use HTTPS**
5. **Set up proper firewall rules**
6. **Regular security updates**

### API Security

- JWT-based authentication
- Rate limiting (configure as needed)
- Input validation
- Encrypted credential storage

## 📈 Scaling

### Horizontal Scaling

- Multiple API instances behind load balancer
- Shared PostgreSQL and Redis
- FAISS indexes can be distributed

### Performance Optimization

- Redis caching for frequent requests
- FAISS index optimization
- Database connection pooling
- Background task processing

## 🆘 Getting Help

1. **Check the documentation**: http://localhost:8000/docs
2. **Run the test suite**: `python scripts/test_system.py`
3. **Check logs** for detailed error messages
4. **Review examples** in the `examples/` directory

## 🎯 Next Steps

After successful setup:

1. **Register your first game** using the API
2. **Integrate with your game client**
3. **Monitor performance** through the stats endpoints
4. **Optimize** based on your game's specific needs

---

🎮 **Happy Gaming!** Your adaptive boss AI system is ready to create engaging, personalized boss encounters!