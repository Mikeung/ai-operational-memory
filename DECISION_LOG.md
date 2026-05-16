# Decision Log

| Date       | Decision                              | Reason                                                        |
|------------|---------------------------------------|---------------------------------------------------------------|
| 2026-05-15 | VPS-first architecture                | Minimize operational overhead for solo-dev context            |
| 2026-05-15 | Advisory-only model                   | Preserve safety and trust; system must never act autonomously |
| 2026-05-15 | SQLite initially                      | Keep bootstrap simple; migrate to Postgres if needed later    |
| 2026-05-15 | FastAPI + uvicorn                     | Lightweight, typed, async-capable, standard Python tooling    |
| 2026-05-15 | pydantic-settings for config          | Type-safe .env loading, no custom parsing                     |
| 2026-05-15 | python-json-logger for structured log | Simple, stdlib-compatible JSON logging                        |
| 2026-05-15 | ruff for lint + format                | Replaces black + isort + flake8 in a single fast tool         |
| 2026-05-15 | No Redis, no Celery                   | Unnecessary at this scale; SQLite + cron is sufficient        |
| 2026-05-15 | No frontend                           | Backend API only; visualization deferred to Phase 5           |
| 2026-05-15 | Lifespan context manager              | FastAPI recommends over deprecated on_event; cleaner teardown |
| 2026-05-15 | Docs URL disabled in production       | Reduce attack surface; enable only with DEBUG=true            |
| 2026-05-15 | Plain dataclasses for topology graph  | No graph DB required; in-memory graph is sufficient for single-repo advisory use; avoids Neo4j/networkx dependency |
| 2026-05-15 | Topology persisted in snapshot payload | Reuses existing SQLite append-only store; no separate topology table needed at this scale |
| 2026-05-15 | Topology recomputed on old snapshots   | Backward compat: GET /topology/* recomputes on-the-fly for snapshots without topology field |
| 2026-05-15 | ss > netstat fallback in ServiceScanner | ss is available on modern Linux; netstat fallback handles older distros/containers |
| 2026-05-15 | Workflow inference is pattern-only     | No ML — deterministic frozenset + package presence checks; explainable, no model deps |
| 2026-05-15 | Cost intelligence is heuristic-only    | No billing API access; observations based on structural patterns + known cost behaviors |
| 2026-05-15 | Recommendations sorted by confidence   | Highest-confidence items shown first; impact used as tiebreaker to prioritize high-risk findings |
| 2026-05-16 | Domain models as vocabulary layer      | topology/domain_models.py adds explicit semantic vocabulary without replacing graph models; clarifies intent without disrupting working systems |
| 2026-05-16 | Observation layer as fact boundary     | cognition/observations.py formally separates scanner facts from topology inferences; every inference above this layer must cite observations below it |
| 2026-05-16 | No folder restructuring in Phase 2.5   | Existing folder layout (scanners/, topology/, memory/, llm_intelligence/) is clear and stable; restructuring would disrupt working imports with no operational benefit |
| 2026-05-16 | llm_intelligence/analyzer.py retained | Placeholder for Phase 3 LLM runtime analysis; not renamed or removed — Phase 3 will populate it |
| 2026-05-16 | Temporal analysis reads snapshot payloads directly | Rather than re-running drift detector on all pairs, temporal engine compares key data fields extracted from stored snapshot data; cheaper and sufficient for pattern detection |
| 2026-05-16 | Prioritization is additive (recs + cost obs + temporal) | Priority engine combines three input streams; temporal volatility acts as a scoring bonus, not a replacement — preserves explainability |
| 2026-05-16 | Attention guidance uses score threshold (0.35) | Items below threshold suppressed; threshold chosen as midpoint of low urgency range — balances noise suppression vs. signal loss |
| 2026-05-16 | CostClass enum added without removing severity | CostClass (LOW/MODERATE/HIGH/EXTREME) is computed from severity + tier; retained both for backward compatibility and richer vocabulary |
| 2026-05-16 | Recommendation urgency/recurrence added with defaults | New fields use Python dataclass defaults so existing serialization and tests remain unbroken |
| 2026-05-16 | Timeline groups by date from created_at prefix | Minimal parsing ([:10] slice) avoids datetime parsing complexity; reliable for SQLite datetime strings |
| 2026-05-16 | Temporal API defaults to 7-day window | 7 days covers a typical sprint; configurable via query param for longer retrospectives |
