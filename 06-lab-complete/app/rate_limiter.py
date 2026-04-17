import time
import redis
from fastapi import HTTPException, status
from .config import settings

# Initialize Redis client
# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_rate_limit(user_id: str):
    """
    Sliding window rate limiter using Redis.
    Limits requests based on RATE_LIMIT_PER_MINUTE.
    """
    now = time.time()
    key = f"rate_limit:{user_id}"
    
    # Create a pipeline for atomic operations
    pipe = redis_client.pipeline()
    
    # Remove old entries outside the window (60 seconds)
    pipe.zremrangebyscore(key, 0, now - 60)
    
    # Count requests in the current window
    pipe.zcard(key)
    
    # Add the current request timestamp
    pipe.zadd(key, {str(now): now})
    
    # Set expiration to clean up unused keys
    pipe.expire(key, 70)
    
    # Execute pipeline
    _, count, _, _ = pipe.execute()
    
    if count >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute.",
            headers={"Retry-After": "60"}
        )
