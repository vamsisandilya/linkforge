"""Redis-backed sliding-window rate limiter.

Uses a sorted set per client keyed by timestamp. On each request we drop
entries older than the window, add the current one, and count what's left —
giving a true rolling window rather than a fixed bucket.
"""

import os
import sys
import time
from functools import lru_cache


@lru_cache
def get_redis():
    use_fake = os.environ.get("USE_FAKE_REDIS") == "1" or (
        "pytest" in sys.modules and os.environ.get("USE_REAL_SERVICES") != "1"
    )
    if use_fake:
        import fakeredis

        return fakeredis.FakeStrictRedis()
    import redis

    return redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


def is_rate_limited(client_key: str, limit: int, window_seconds: int = 60) -> bool:
    r = get_redis()
    now = time.time()
    key = f"rl:{client_key}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zadd(key, {f"{now}:{os.urandom(4).hex()}": now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds)
    _, _, count, _ = pipe.execute()
    return count > limit
