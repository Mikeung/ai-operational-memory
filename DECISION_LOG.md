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
| 2026-05-16 | psutil for runtime scanner             | psutil provides cross-platform resource readings with graceful fallbacks; already installed (v7.2.2); lightweight and VPS-appropriate |
| 2026-05-16 | RuntimeScanner registered in global registry | Consistent with existing scanner pattern; results stored in snapshot payload under runtime_health; no separate scan endpoint needed |
| 2026-05-16 | SeverityEngine uses 5 weighted factors | Runtime instability (30%), recommendation signal (25%), temporal volatility (20%), recurrence (15%), cost amplification (10%); weights reflect operational priority on a VPS |
| 2026-05-16 | RecurrenceEngine uses string-prefix matching | Title+category prefix up to 60/70 chars; robust to minor wording variation while avoiding false grouping; deterministic, no ML |
| 2026-05-16 | RuntimeTopologyFusion accepts dicts not objects | Avoids circular imports; works with both live topology objects and stored snapshot payloads; consistent with digest/report generation pattern |
| 2026-05-16 | Three digest types: daily/morning/critical | Different operator use-cases: daily = full picture, morning = trend-first, critical = immediate-action only; each tailored to decision context |
| 2026-05-16 | runtime_concerns added to AttentionReport | Live runtime signals are qualitatively different from recommendation-derived signals; separate field prevents noise mixing and enables targeted routing in digests |
| 2026-05-16 | Recommendation urgency/recurrence added with defaults | New fields use Python dataclass defaults so existing serialization and tests remain unbroken |
| 2026-05-16 | Timeline groups by date from created_at prefix | Minimal parsing ([:10] slice) avoids datetime parsing complexity; reliable for SQLite datetime strings |
| 2026-05-16 | Temporal API defaults to 7-day window | 7 days covers a typical sprint; configurable via query param for longer retrospectives |
| 2026-05-16 | InvestigationEngine uses dispatch table | Dict mapping kind → handler function; clean extension pattern without if/elif chains; VALID_KINDS frozenset enforced at entry point |
| 2026-05-16 | ComparisonEngine computes SeverityDelta by running SeverityEngine on both snapshots | Severity not stored in snapshots; recomputed from data fields; ensures consistency with current severity model |
| 2026-05-16 | ContinuityEngine appended to recurrence.py | Related tracking logic kept in one file; avoids unnecessary file proliferation; RecurrenceEngine and ContinuityEngine share helper functions |
| 2026-05-16 | PatternLibrary has 9 deterministic signatures | No ML, no embeddings, no vector search; patterns are explicit frozenset intersections on package names, workflow types, provider counts; fully auditable |
| 2026-05-16 | Bounded language rules enforced by convention | Explanation system prohibits certainty claims (will/causes/proves) via documented rules and bounded qualifiers list; no automated enforcement — relies on code review |
| 2026-05-16 | EvidenceTree depth hard-capped at 3 | Prevents unbounded tree growth; depth 3 (conclusion → factor → sub-evidence) covers all meaningful operational traces without cognitive overload |
| 2026-05-16 | Investigation router uses get_by_id() not get_snapshot_by_id() | SnapshotEngine exposes get_by_id(); naming mismatch caught during test integration; fixed before commit |
| 2026-05-16 | B008 and E741 added to ruff ignore | B008 (FastAPI Depends in defaults) is the accepted FastAPI pattern; E741 (ambiguous l variable names) found in continuity iteration patterns — suppressed globally |
| 2026-05-16 | HeuristicRegistry as frozen dataclass registry | Single source of truth for all numeric thresholds across cognition modules; immutable at runtime; no rules engine — just named constants with documentation |
| 2026-05-16 | theme_minimum_evidence = 2.0 | A single signal may be incidental; 2+ signals constitute a theme; prevents single-data-point themes from polluting ecosystem summaries |
| 2026-05-16 | 5 named concern clusters (rule-based only) | high_cost_llm_processing, unstable_orchestration, provider_risk, runtime_degradation, cost_accumulation; each activates from explicit signal intersection — no clustering algorithms, no ML |
| 2026-05-16 | Clusters explicitly labeled as organizational aids | Note field states "clusters are organizational aids — not causal assertions"; prevents misuse of clustering output as diagnosis |
| 2026-05-16 | Drift uses early-third vs recent-third window split | Avoids point-in-time comparison artifacts; 1-snapshot comparisons too noisy; thirds provide stability while still detecting trend direction |
| 2026-05-16 | Consolidation is 3-pass (category → evidence → cluster) | Category grouping first (deterministic), then evidence keyword overlap (shared signal detection), then cluster bridging (cross-category); each pass is auditable independently |
| 2026-05-16 | ConsolidatedConcern preserves source rec titles | Traceability requirement: every consolidated concern must name all contributing recommendations so operator can trace back to originating evidence |
| 2026-05-16 | Ecosystem synthesis engine is strictly deterministic | No LLM cognition, no embeddings, no vector search; all theme extraction uses explicit pattern-name intersections and category-set matching |
| 2026-05-16 | Bounded language enforced in all ecosystem reports | Reports use "appears to", "evidence suggests", "historically associated with"; certainty words (will/causes/proves) prohibited per operational philosophy |
| 2026-05-16 | Schema version "1.0" established as canonical baseline | SnapshotValidator stabilizes current snapshot structure without redesigning it; optional sections filled by normalize(), not enforced as errors |
| 2026-05-16 | Confidence = evidence density, NOT probability | ConfidenceNormalizer uses weighted blend of raw score + evidence count + snapshot depth; interpretation bands label strength only; all report notes carry "not a probability of correctness" advisory |
| 2026-05-16 | Validation warns, never auto-corrects | CognitionValidator detects internal inconsistencies (e.g., degrading health with no themes) and surfaces them to operators; outputs are unchanged |
| 2026-05-16 | Query workflows are structured inquiry, not chatbot | OperatorQueryWorkflow produces deterministic step-by-step analysis from explicit inputs; no conversational interface, no LLM-generated findings |
| 2026-05-16 | clean_snapshots excludes info findings | AuditReport.clean_snapshots counts snapshots with no errors or warnings; info-level volume notes do not mark a snapshot as dirty |
| 2026-05-16 | Benchmarks are standalone scripts, not pytest | benchmarks/ uses perf_counter with 10-run averaging; isolated from test suite to prevent slow CI runs |
| 2026-05-16 | Stability router groups Phase 7 endpoints | /stability/* prefix avoids polluting existing router prefixes; covers schema, confidence, validation, audit in one focused router |
