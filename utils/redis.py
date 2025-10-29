import redis
import threading

import settings


__all__ = ("get_redis",)


_serve_redis = None
_redis_lock = threading.Lock()


def get_redis() -> redis.Redis:
    """
    线程安全的 Redis 连接实例
    """
    global _serve_redis
    if _serve_redis is None:
        with _redis_lock:
            if _serve_redis is None:
                _redis_pool = redis.ConnectionPool(
                    **settings.REDIS_CONFIG,
                    decode_responses=True,
                    max_connections=settings.REDIS_CONNECTION_POOL_COUNT,
                )
                _serve_redis = redis.Redis(connection_pool=_redis_pool)
    return _serve_redis