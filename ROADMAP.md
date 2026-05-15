# Roadmap

## Phase 0 — Foundation ✓ Complete
- [x] Repo bootstrap
- [x] Governance documents
- [x] FastAPI skeleton with lifecycle hooks
- [x] Structured JSON logging
- [x] Docker Compose setup
- [x] SQLite operational store
- [x] pyproject.toml + ruff + mypy + pytest
- [x] Health endpoint

## Phase 1 — Infrastructure Understanding
- [ ] RepoScanner: full implementation (file tree, language detection, dependency detection)
- [ ] ProcessScanner: classify processes by type (web server, LLM daemon, DB, etc.)
- [ ] DockerScanner: detect running containers and compose stacks
- [ ] Wire scanners → SQLite store
- [ ] `/scan` API endpoint
- [ ] Runtime summary generation

## Phase 2 — Operational Memory
- [ ] Periodic snapshot scheduler (APScheduler or cron)
- [ ] Snapshot diff engine: detect structural drift
- [ ] Historical scan comparison
- [ ] `/snapshots` and `/diff` API endpoints

## Phase 3 — LLM Intelligence
- [ ] Detect LLM API calls in code and process lists
- [ ] Model identification (gpt-4, claude-*, etc.)
- [ ] Estimate token cost from usage patterns
- [ ] WHAT / WHEN / WHERE / WHICH classification
- [ ] Routing quality analysis
- [ ] `/llm-analysis` API endpoint

## Phase 4 — Recommendation Engine
- [ ] Operational review generator
- [ ] Cost efficiency recommendations
- [ ] LLM routing recommendations
- [ ] Scheduled weekly report generation
- [ ] `/recommendations` API endpoint

## Phase 5 — Visualization
- [ ] Topology graph construction
- [ ] Service relationship mapping
- [ ] Optional: lightweight React Flow frontend
