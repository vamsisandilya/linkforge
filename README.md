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

## How it's built

**Cache-aside on the redirect path.** `GET /{code}` checks Redis for `code -> target_url`
first, and only queries Postgres on a miss, then writes the result back to Redis
(`links/cache.py`). This is the one endpoint where speed matters most, so it's the one I
optimized for latency. The downside: a cached entry can keep serving a link that was just
edited or deleted, until the TTL (1 hour) runs out. That's an acceptable tradeoff here since
link targets don't really change once created.

**Clicks are recorded off the request path.** Every redirect queues a Celery task
(`links/tasks.py`) instead of writing the `Click` row directly, so a slow database write never
adds to redirect latency. The tradeoff: click counts are eventually consistent. If you call
`/stats/` right after a redirect, the click might not show up yet. And if the worker is down,
clicks just stop being recorded, with no error to tell you that happened.

**Rate limiting uses a sliding window, not a fixed one.** `links/ratelimit.py` keeps a Redis
sorted set per client. On each request it removes anything older than the window and counts
what's left. A fixed window (`INCR` + `EXPIRE`) would be cheaper, one Redis call instead of a
pipeline, but it lets a client send a burst of requests right at the boundary between two
windows and get through twice as much traffic as the limit allows. I picked the more correct
option here since this is the part of the API meant to stop abuse.

**The composite index on `Click` wasn't actually being used.** `Click` has an index on
`(link, created_at)`, added because I assumed the analytics endpoint would need it. It didn't,
at first: the original `/stats/` endpoint pulled a link's entire click history with no date
limit, so Postgres just used the smaller `link_id` index and sorted the results itself. The
composite index sat there unused, still costing a bit of extra work on every insert, with no
benefit on reads. I only found this by running `EXPLAIN ANALYZE` against about 30k seeded
clicks — I hadn't actually checked whether the query planner was using the index, I'd just
assumed it was. Adding an optional `?days=N` filter gave the planner a reason to use it:
without the filter the query took 18.5ms, with `?days=7` it dropped to 2.2ms, scanning about
2.4k rows instead of 32k. Adding an index doesn't mean the database will use it — you have to
check.

## Benchmarks

Measured with `k6` against the Docker Compose stack (single Postgres container, single Redis
container, Django's dev server — not a production ASGI setup, so treat these as relative, not
absolute).

Redirect traffic drawn from a pool of 300 codes out of 100k seeded links, to mimic the way
real traffic skews toward a small set of popular links rather than hammering one code:

| | Cache-aside (Redis) | No cache (Postgres every time) |
|---|---|---|
| Throughput | 262 req/s | 147 req/s |
| p95 latency | 313ms | 410ms |
| avg latency | 144ms | 256ms |

Cache hit rate settled around 98% (300 misses to populate the pool, the rest served from
Redis). This gap only shows up once traffic is spread across enough different codes that
Postgres actually has to do work for each request. A load test that hits the same single code
over and over hides this almost completely, because Postgres just keeps serving the same warm
row regardless of whether Redis is involved. I tried that first and saw basically no
difference between cached and uncached — the pooled test above is what it took to see a real
number.

Test coverage: 7 tests, 97% on `links/*` (`coverage run -m pytest && coverage report
--include="links/*"`).

## Load-testing it yourself

```bash
# single code, quick sanity check on redirect latency
k6 run -e CODE=<code> loadtest/redirect.js

# realistic pooled traffic, what the numbers above came from
k6 run loadtest/redirect_pool.js
```

`loadtest/hot_codes.json` is a sample pool of codes from my own seeded dataset — regenerate
it against your own data if the codes don't exist in your DB.

## Things I'd add next

Geo/referrer enrichment on click records, QR code generation for links, a scheduled job to
purge expired links instead of just checking `expires_at` on read, and probably
`task_ignore_result=True` on the Celery config — right now every click task stores a result
in Redis nobody ever reads, which is just wasted memory.
