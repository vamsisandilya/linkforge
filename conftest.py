import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _reset_state():
    """Keep cache + fake redis clean between tests."""
    from django.core.cache import cache

    cache.clear()
    try:
        from links.ratelimit import get_redis

        get_redis().flushall()
    except Exception:
        pass
    yield
