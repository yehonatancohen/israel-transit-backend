# Israel Transit MVP Backend

FastAPI backend for an Israel public-transit routing MVP with AI-assisted reranking and delay-aware transfer slack.

## Key features
- GTFS loader (upload a GTFS ZIP, or mount it) and basic schedule query.
- Earliest-arrival search up to 2 transfers with configurable minimum transfer slack.
- Delay-aware routing using a simple historical lateness model per corridor/hour bucket.
- Live session tracking + opportunistic re-routing suggestions during the trip.
- AI reranker via OpenRouter (optional). Falls back to heuristics if no key.
- OpenAPI docs (Swagger UI) at `/docs` and JSON at `/openapi.json`.
- Dockerfile, `.env.example`, tests, and Makefile.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill OPENROUTER_API_KEY if you want AI reranking, else leave empty

# Run dev server
uvicorn app.main:app --reload --port 8080
# Swagger:           http://localhost:8080/docs
# OpenAPI JSON:      http://localhost:8080/openapi.json
```

### Using Docker
```bash
docker build -t israel-transit-mvp:latest .
docker run --rm -p 8080:8080 --env-file .env israel-transit-mvp:latest
```

## Data
By default the backend will attempt to hydrate its GTFS tables from the
[Curlbus API](https://curlbus.app/).  Set `CURLBUS_API_BASE` if you need a
different endpoint or leave it empty to disable the fetch.

You can still supply your own static schedules: put a GTFS ZIP under
`data/gtfs/il_gtfs.zip` or upload via `/v1/feeds/gtfs/upload`.

Realtime ingestion: `/v1/feeds/realtime/ingest` accepts normalized JSON events;
map GTFS‑RT externally.

## Environment
- `OPENROUTER_API_KEY`: Optional for AI reranking via OpenRouter.
- `OPENROUTER_MODEL`: Optional. Defaults to `openrouter/auto`.
- `APP_SECRET_KEY`: Any string. Default is auto-generated at first run.
- `MIN_TRANSFER_SLACK_SECONDS`: Default 300 (5 min). Increased adaptively by lateness model.
- `ROUTER_MAX_TRANSFERS`: Default 2.
- `ROUTER_DEPARTURE_WINDOW_MIN`: Default 45 (search trips leaving within this many minutes).

## Tests
```bash
pytest -q
```

## Notes
This MVP implements a practical baseline. It supports:
- nearest-stop lookup by coordinates
- direct and 1–2 transfer searches
- transfer slack raised when feeder corridors are historically late
- on-trip progress and re-route suggestions

You will still need to wire a production-grade router and robust GTFS‑RT ingestion at scale. The code cleanly isolates these concerns.
