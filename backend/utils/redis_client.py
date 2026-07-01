import os
import redis

# Redis connection string
# Fallback to local Docker setup if not provided in .env
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create a global Redis connection pool
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

def get_redis_client() -> redis.Redis:
    """
    Returns a configured Redis client using the global connection pool.
    decode_responses=True ensures we get Python strings instead of bytes.
    """
    return redis.Redis(connection_pool=redis_pool)
