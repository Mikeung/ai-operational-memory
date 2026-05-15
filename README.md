# AI Operational Memory

A continuously running operational intelligence and memory layer for AI agent ecosystems.

> **Observe automatically. Decide manually.**

---

## What This Is

AI Operational Memory scans your infrastructure, repositories, and running processes to build a continuously updated operational picture. It stores that picture in a queryable memory layer, tracks drift over time, analyzes LLM usage patterns, and surfaces actionable recommendations.

It is strictly advisory. It never modifies code, infrastructure, or deployments.

---

## Quick Start

### Local

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn backend.main:app --reload
```

Visit `http://localhost:8000/health` to confirm it's running.

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

---

## Endpoints

| Method | Path      | Description              |
|--------|-----------|--------------------------|
| GET    | `/`       | Service identity         |
| GET    | `/health` | Uptime and version check |

Swagger UI available at `/docs` when `DEBUG=true`.

---

## Project Layout

```
backend/           FastAPI application core
scanners/          Read-only infrastructure scanners
memory/            SQLite-based operational store
topology/          Service topology builder
llm_intelligence/  LLM usage analysis
observability/     Structured logging setup
tests/             Pytest suite
docker/            Dockerfile
docs/              Architecture, decisions, roadmap docs
scripts/           Utility scripts
data/              SQLite DB (gitignored, created at runtime)
```

---

## Development Commands

```bash
make install      # Install with dev deps
make dev          # Run with hot reload
make test         # Run test suite
make lint         # Ruff linting
make fmt          # Ruff formatting
make typecheck    # mypy strict check
make check        # lint + typecheck + test
make docker-up    # Start via Docker Compose
make docker-down  # Stop Docker Compose
```

---

## Roadmap

| Phase | Focus                          | Status      |
|-------|--------------------------------|-------------|
| 0     | Foundation bootstrap           | Complete    |
| 1     | Infrastructure scanning        | Planned     |
| 2     | Operational memory & drift     | Planned     |
| 3     | LLM intelligence analysis      | Planned     |
| 4     | Recommendation engine          | Planned     |
| 5     | Visualization & reporting      | Planned     |

---

## License

MIT
