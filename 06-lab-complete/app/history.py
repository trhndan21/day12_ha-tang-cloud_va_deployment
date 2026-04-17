import redis
import json
from .config import settings

# Handle rediss:// (SSL) only if it's explicitly used in the URL
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def save_message(user_id: str, role: str, content: str):
    """
    Save a message to the user's conversation history in Redis.
    Limits history to the last 10 messages.
    """
    key = f"history:{user_id}"
    message = {"role": role, "content": content}
    
    # Push to list and trim
    redis_client.lpush(key, json.dumps(message))
    redis_client.ltrim(key, 0, 9)
    # Expire after 24 hours of inactivity
    redis_client.expire(key, 24 * 3600)

def get_history(user_id: str):
    """
    Retrieve conversation history for a user.
    """
    key = f"history:{user_id}"
    history_raw = redis_client.lrange(key, 0, -1)
    # Return in chronological order (Redis lrange 0 -1 returns from left to right)
    # Since we lpush, 0 is the newest. We want oldest first for LLM context.
    history = [json.loads(m) for m in history_raw]
    return list(reversed(history))
