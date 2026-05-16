# AI Operational Memory

**Operational intelligence and memory for AI ecosystems.**

> Observe automatically. Decide manually.

---

## What This Is

AI Operational Memory is a continuously running backend service that scans your infrastructure — repositories, running processes, containers, network ports — builds an operational topology map, tracks drift over time, analyzes LLM usage patterns, and surfaces advisory recommendations.

It gives you a clear, evidence-based picture of what your AI system is doing and how it is changing. You remain in control of every decision.

---

## What This Is NOT

- **Not an agent framework.** It does not orchestrate AI agents.
- **Not an orchestration engine.** It does not execute workflows.
- **Not autonomous infrastructure control.** It never modifies code, config, or deployments.
- **Not a generic dashboard.** It is purpose-built for AI ecosystem understanding.
- **Not a billing system.** Cost observations are structural estimates, not measured spend.

---

## Why It Exists

AI systems evolve faster than humans can track manually:

- LLM providers get swapped without documentation
- New workflows appear between repositories with no cross-team visibility
- Token costs grow silently until a billing alert fires
- Architecture drift accumulates across sprints
- No one knows what the system actually does at 3am on Tuesday

AI Operational Memory restores that visibility — continuously, automatically, without manual documentation effort.

---

## Core Capabilities

| Capability | What it does |
|---|---|
| **Scanning** | Reads repos, processes, ports, and containers. Never writes. |
| **Topology reconstruction** | Builds a graph of assets, SDKs, frameworks, and their relationships |
| **Workflow inference** | Identifies AI workflow patterns (RAG, Telegram bot, multi-agent, etc.) |
| **Drift detection** | Tracks what changed between scans — LLM providers, frameworks, Docker, CI |
| **LLM cost intelligence** | Flags structural cost risk patterns from usage topology |
| **Recommendation generation** | Produces advisory recommendations with evidence chains |
| **Operational memory** | Appends every scan to SQLite — queryable history, never overwritten |

---

## Core Principles

**Facts first, inference second.**
Every inference — topology edge, workflow pattern, recommendation — cites the raw evidence that produced it. Nothing is asserted without a source.

**Observe automatically, decide manually.**
The system scans and reports. Humans act. There is no autonomous remediation path.

**Explainability over sophistication.**
Deterministic heuristics with visible reasoning beat opaque ML models with no explanation. Every confidence score is traceable.

**Topology is derived, not authoritative.**
The topology graph is reconstructed from observed evidence at scan time. It is a working hypothesis, not a ground-truth registry.

**Append-only operational history.**
Snapshots are never overwritten. Historical state is always recoverable.

---

## Quickstart

### Local

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn backend.main:app --reload
```

```bash
# Confirm running
curl http://localhost:8000/health

# Trigger a scan
curl -X POST http://localhost:8000/scan -H 'Content-Type: application/json' -d '{"target": "."}'

# Fetch topology
curl http://localhost:8000/topology/latest

# Fetch workflow inferences
curl http://localhost:8000/topology/workflows

# Fetch advisory recommendations
curl http://localhost:8000/topology/recommendations
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service identity |
| GET | `/health` | Uptime and version |
| POST | `/scan` | Trigger full operational scan |
| GET | `/scan/status` | Scanner registry and scheduler status |
| GET | `/snapshots` | List all stored snapshots |
| GET | `/snapshots/{id}` | Fetch a specific snapshot |
| GET | `/reports/latest` | Markdown report from latest scan |
| GET | `/topology/latest` | Topology graph (nodes + edges) |
| GET | `/topology/workflows` | Inferred workflow patterns |
| GET | `/topology/recommendations` | Advisory recommendations |
| GET | `/topology/report` | Topology markdown report |

Swagger UI available at `/docs` when `DEBUG=true`.

---

## Repository Layout

```
backend/           FastAPI application — routes, lifecycle, config
scanners/          Read-only infrastructure scanners (repo, service, process)
cognition/         Observation layer — normalized facts from scanner output
topology/          Topology builder, workflow inference, domain models
llm_intelligence/  LLM cost intelligence and usage analysis
reports/           Markdown report generator, recommendation engine
memory/            Append-only SQLite operational store, drift detection
observability/     Structured JSON logging setup
tests/             Pytest suite (unit + integration)
docs/              Architecture, decisions, API overview
docker/            Dockerfile
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

## Architecture

```
Scanners (read-only)
  → Cognition / Observations (facts)
    → Topology Builder (graph + evidence)
    → Workflow Inference (pattern matching)
    → LLM Cost Intelligence (heuristic observations)
      → Recommendation Engine (advisory output)
        → Operational Memory (SQLite, append-only)
          → FastAPI (HTTP reports + queries)
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a full layer-by-layer explanation.

---

## Operational Discipline

This system follows a strict PM-authority model:

- The **PM defines** product direction and approves phases
- **Claude (Claude Code)** implements, tests, commits, and reports
- Every completed task updates `TASK_LOG.md` and `DECISION_LOG.md`
- Every phase is committed to git with a traceable message

---

## License

MIT
