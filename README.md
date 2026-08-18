# Linkforge

A URL shortener with click analytics, built with Django + DRF. Redirects are served
cache-aside off Redis, clicks are recorded asynchronously via Celery so they never sit on
the request path, and link creation is protected by a sliding-window rate limiter.

**Stack:** Django · DRF · PostgreSQL · Redis · Celery · Docker · GitHub Actions

## Running it

```bash
cp .env.example .env
docker compose up --build          # api + postgres + redis + celery worker
```

```bash
# Create a link
curl -X POST http://localhost:8000/api/links/ \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'
# -> {"code": "aB3xY7z", "short_url": "http://localhost:8000/aB3xY7z", ...}

# Follow it (302 redirect, click tracked asynchronously)
curl -i http://localhost:8000/aB3xY7z

# See analytics
curl http://localhost:8000/api/links/aB3xY7z/stats/
```

### Running the tests

No Docker needed for this part — the suite runs against SQLite, a local-memory cache, and
eager Celery by default, so it's fast and has zero external dependencies.

```bash
pip install -r requirements.txt
pytest -q
```

CI runs the same suite against real Postgres and Redis containers instead (see
`.github/workflows/ci.yml`).

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/links/` | Create a short link (rate-limited) |
| GET | `/{code}` | Redirect (302) + async click tracking |
| GET | `/api/links/{code}/stats/` | Total clicks, clicks-by-day, top referrers. Accepts `?days=N` to bound the range |
