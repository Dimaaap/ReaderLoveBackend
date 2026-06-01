from redis.asyncio import Redis

from core.config import settings

redis_client = Redis.from_url(
    settings.redis.redis_url,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5,
)
