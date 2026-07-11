import hashlib
import json
import logging
import functools
from .redis_client import get_redis_client

logger = logging.getLogger(__name__)

class AiONCache:
    """
    Smart Caching Layer for yAI.
    Caches LLM responses, generated code, and search results to improve execution speed.
    """
    def __init__(self):
        self.redis = get_redis_client()
        # Fallback in-memory cache if Redis is unavailable
        self._memory_cache = {}

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generates a stable cache key based on the input parameters."""
        # Convert kwargs to a stable JSON string
        try:
            stable_json = json.dumps(kwargs, sort_keys=True)
            hashed = hashlib.sha256(stable_json.encode('utf-8')).hexdigest()
            return f"aion:cache:{prefix}:{hashed}"
        except TypeError:
            # Fallback if kwargs are not JSON serializable
            return f"aion:cache:{prefix}:{hash(str(kwargs))}"

    def get(self, prefix: str, **kwargs):
        key = self._generate_key(prefix, **kwargs)
        if self.redis:
            try:
                val = self.redis.get(key)
                if val:
                    logger.info(f"[CACHE HIT] Redis cache hit for {prefix}")
                    return json.loads(val)
            except Exception as e:
                logger.error(f"[CACHE ERROR] Failed to read from Redis: {e}")
        
        # Fallback to in-memory
        if key in self._memory_cache:
            logger.info(f"[CACHE HIT] Memory cache hit for {prefix}")
            return self._memory_cache[key]
            
        return None

    def set(self, prefix: str, value: any, ttl_seconds: int = 3600, **kwargs):
        key = self._generate_key(prefix, **kwargs)
        if self.redis:
            try:
                self.redis.setex(key, ttl_seconds, json.dumps(value))
                return
            except Exception as e:
                logger.error(f"[CACHE ERROR] Failed to write to Redis: {e}")
                
        # Fallback to in-memory
        self._memory_cache[key] = value

# Global cache instance
cache = AiONCache()

def llm_cache(prefix="llm"):
    """
    Decorator to cache LLM invocations.
    Usage:
    @llm_cache("coder_agent")
    def run(self, state):
        ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, state, *args, **kwargs):
            # Extract relevant state for caching (e.g. goal, project_id, etc.)
            cache_keys = {
                "goal": state.get("goal"),
                "agent": prefix
            }
            cached_result = cache.get(prefix, **cache_keys)
            
            if cached_result:
                # Merge cached state updates into current state
                state.update(cached_result)
                return state
                
            # Run the actual function
            new_state = func(self, state, *args, **kwargs)
            
            # Cache the diff (what this agent added to the state)
            diff = {k: v for k, v in new_state.items() if k not in cache_keys and k != "execution_logs"}
            cache.set(prefix, diff, ttl_seconds=86400, **cache_keys)
            
            return new_state
        return wrapper
    return decorator
