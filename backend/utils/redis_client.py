import os
import redis

# Redis connection string
# Fallback to local Docker setup if not provided in .env
REDIS_URL = os.getenv("REDIS_URL", None)

# Create a global Redis connection pool if URL is provided
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True, socket_timeout=2) if REDIS_URL else None

def get_redis_client():
    """
    Returns a configured Redis client using the global connection pool.
    Returns None if Redis is not configured.
    """
    if not redis_pool:
        return None
    return redis.Redis(connection_pool=redis_pool)


