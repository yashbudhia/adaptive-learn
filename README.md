docker run -d --name redis-adaptive -p 6379:6379 redis:latest
python -m uvicorn app.main:app --reload 