"""Cache-aside layer for the redirect hot path.

The redirect endpoint is read-heavy and latency-sensitive, so we resolve
code -> target_url from Redis first and only fall back to Postgres on a miss,
warming the cache on the way out.
"""

from django.core.cache import cache

CACHE_TTL = 3600  # seconds


def _key(code: str) -> str:
    return f"link:{code}"


def get_cached_target(code: str):
    return cache.get(_key(code))


def set_cached_target(code: str, target: str, ttl: int = CACHE_TTL):
    cache.set(_key(code), target, ttl)


def invalidate(code: str):
    cache.delete(_key(code))
