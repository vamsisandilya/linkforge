from datetime import timedelta

import pytest
from django.utils import timezone

from links.cache import get_cached_target
from links.models import Click, Link


@pytest.mark.django_db
def test_create_link_generates_code(api_client):
    resp = api_client.post(
        "/api/links/", {"target_url": "https://example.com"}, format="json"
    )
    assert resp.status_code == 201
    assert resp.data["code"]
    assert resp.data["short_url"].endswith(resp.data["code"])


@pytest.mark.django_db
def test_redirect_returns_302_and_records_click(api_client):
    link = Link.objects.create(code="abc123", target_url="https://example.com")
    resp = api_client.get("/abc123/")
    assert resp.status_code == 302
    assert resp["Location"] == "https://example.com"
    # click recorded via (eager) celery task
    assert Click.objects.filter(link=link).count() == 1


@pytest.mark.django_db
def test_redirect_warms_the_cache(api_client):
    Link.objects.create(code="cache1", target_url="https://cached.example")
    assert get_cached_target("cache1") is None
    api_client.get("/cache1/")
    assert get_cached_target("cache1") == "https://cached.example"


@pytest.mark.django_db
def test_expired_link_returns_410(api_client):
    Link.objects.create(
        code="old1",
        target_url="https://x.example",
        expires_at=timezone.now() - timedelta(days=1),
    )
    resp = api_client.get("/old1/")
    assert resp.status_code == 410


@pytest.mark.django_db
def test_unknown_code_returns_404(api_client):
    resp = api_client.get("/missing/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_stats_aggregates_clicks(api_client):
    link = Link.objects.create(code="stat1", target_url="https://x.example")
    for _ in range(3):
        Click.objects.create(link=link, referrer="https://ref.example")
    resp = api_client.get("/api/links/stat1/stats/")
    assert resp.status_code == 200
    assert resp.data["total_clicks"] == 3
    assert resp.data["top_referrers"][0]["referrer"] == "https://ref.example"


@pytest.mark.django_db
def test_rate_limit_blocks_excess_creates(api_client, settings):
    settings.CREATE_RATE_LIMIT = 3
    statuses = [
        api_client.post(
            "/api/links/", {"target_url": "https://e.example"}, format="json"
        ).status_code
        for _ in range(6)
    ]
    assert 429 in statuses
    assert statuses.count(201) <= 3
