import redis
from datetime import datetime
from fastapi import HTTPException, status
from .config import settings

# Initialize Redis client
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_budget(user_id: str, estimated_cost: float = 0.01):
    """
    Budget tracker using Redis.
    Tracks monthly spending per user.
    """
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    # Get current spending
    current_spending = float(redis_client.get(key) or 0.0)
    
    if current_spending + estimated_cost > settings.MONTHLY_BUDGET_USD:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly budget of ${settings.MONTHLY_BUDGET_USD} exceeded."
        )
    
    # Increment spending
    redis_client.incrbyfloat(key, estimated_cost)
    # Expire after 32 days to clean up old months
    redis_client.expire(key, 32 * 24 * 3600)

def get_current_spending(user_id: str) -> float:
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    return float(redis_client.get(key) or 0.0)
