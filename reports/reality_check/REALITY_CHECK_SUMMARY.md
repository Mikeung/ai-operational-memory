# Reality Check Summary
First Real VPS Deployment — 2026-05-17

This report determines future roadmap direction.

---

## What Worked

### Core pipeline — fully functional
Repo scanner → topology → workflow inference → recommendations → snapshot storage
executed end-to-end in 0.6–1.15s per target. SQLite storage is clean and efficient.
The pipeline is production-viable on a single VPS.

### Telegram delivery — works as designed
5 messages sent, 0 failures, <300ms average latency.
Daily digest format is readable and appropriately compressed for mobile.
Duplicate suppression and routing logic work correctly.
This is the highest-value deliverable of the recent phases.

### Workflow inference — the strongest signal
TELEGRAM_LLM_PIPELINE at 0.88 confidence is accurate for telegram-humint.
MULTI_PROVIDER_ORCHESTRATION at 0.82 for ai-operational-memory is correct.
This feature would provide real value to an operator encountering a codebase cold.

### Scan speed — appropriate for VPS
0.6–1.15s per full scan is fast enough for 5-minute intervals without meaningful
scheduler load. Three simultaneous targets would complete in ~3s.

### Storage baseline — no immediate pressure
53 KB for 4 snapshots. SQLite fragmentation: 0. The storage pipeline is clean.
Projected 30-day steady-state is manageable (~300 MB) with retention active.

---

## What Failed

### Service is not daemonized
There is no systemd unit for ai-operational-memory. The scheduler is never started.
This is the single most critical gap: the entire periodic scan + digest + alert
pipeline only works when someone manually invokes Python.

**This must be the first fix.**

### Topology pollution
The service scanner reads all listening ports on the system, not just those
attributable to the scanned target. Every scan of every project includes nodes
for Redis, PostgreSQL, Elasticsearch, nginx, and all other co-resident services.

On a multi-project VPS (which is the real deployment environment), this makes
topology untrustworthy. Nodes are counts of "things running on the VPS," not
"things this project uses."

### Priority field is null on all recommendations
Every recommendation came back with `priority: null`. This field should be
set to `high/medium/low` by the recommendation engine. Without it, the operator
cannot triage.

---

## What Appears Useful

**Workflow inference** — accurate, fast, non-obvious to derive manually.
Real value for onboarding or auditing an unfamiliar codebase.

**Telegram daily digest** — the right format, right channel, right compression.
"What matters right now?" answered in ~400 chars.

**Survivability framework** — conceptually sound. Will provide real value after
7+ days of continuous operation when baselines exist.

**Storage hygiene / retention engine** — well-designed. Advisory-only approach
is correct. Will become essential once steady-state snapshot volume accumulates.

---

## What Appears Noisy

**Recommendations are template-driven, not project-specific.** The same 3–4
recommendations fire for every LLM-using project:
1. "Add request-level latency tracking" — fires regardless of existing observability
2. "No vector store detected" — fires on every LLM project, including VPS with Elasticsearch running
3. "Multiple premium providers" — fires whenever both OpenAI and Anthropic are detected

These are not wrong, but they are not useful at the 10th repetition. They will
dominate digests and create operator fatigue quickly.

**Runtime health score 1.0 everywhere** — no signal value. Either the thresholds
are never triggered in real conditions, or the scanner doesn't have data to work with.

---

## What Appears Operationally Expensive

**Storage at full operation:** 3 targets × 288 scans/day (5-min interval) = 864
snapshots/day × ~13 KB = ~11 MB/day. 30-day retention = ~330 MB steady-state.
This is manageable but requires retention to run on schedule, which requires the
scheduler to be active.

**Topology with VPS-wide service discovery:** On a VPS with 20+ services, every
scan produces a 60–80 node topology. Most nodes are noise. The topology builder
running on a larger VPS would produce increasingly useless output.

---

## High-Value Reports

| Report | Value | Reason |
|---|---|---|
| Workflow inference | HIGH | Accurate, non-obvious, actionable |
| Telegram daily digest | HIGH | Right channel, right compression |
| Survivability report | MEDIUM (future) | Needs baseline history to be meaningful |
| Ecosystem review | MEDIUM | Useful for first-look audits |
| Storage optimizer | MEDIUM (future) | Useful once volume accumulates |

## Low-Value Reports (currently)

| Report | Value | Reason |
|---|---|---|
| Runtime health (score 1.0) | LOW | No signal variance observed |
| Recommendations list | LOW (current) | Generic, priority null, repeats across projects |
| Scaling boundaries | LOW (current) | No data to compare against |
| Investigation quality | LOW (current) | No investigation results yet |

---

## Recommended Tuning Priorities

### Priority 1 — Deploy as daemon (blocker)
Create a systemd unit for ai-operational-memory on a non-conflicting port (8080).
Without this, the periodic scan pipeline, daily digest, and critical alerts are
inoperative.

### Priority 2 — Fix topology attribution
The service scanner should attempt to attribute ports to the target project before
adding them to topology. Simplest approach: only include ports that appear in the
target project's config files, docker-compose, or requirements. Unattributable
ports go into a "shared infrastructure" category, not the project topology.

### Priority 3 — Fix recommendation priority field
The recommendation engine should always set `priority` to `high/medium/low`.
The field exists in the schema but is populated as null. Triage is impossible
without it.

### Priority 4 — Recommendation deduplication / suppression
After 3 consecutive scans where the same recommendation fires, it should be
demoted to the weekly digest and not the daily. "No vector store detected"
should be suppressible once the operator has acknowledged it.

### Priority 5 — Accumulate baseline history
Start the scheduler and let it run for 7 days without intervention. The temporal
analysis, drift detection, survivability, and storage pressure features all depend
on this baseline. The system is under-utilized until it has history.

### Deferred

- Runtime health thresholds (needs investigation — possibly a scanner data gap)
- Per-project LLM event ingestion (valuable but requires operator integration work)
- Investigation quality / triage features (Phase 13C — no investigations running yet)

---

## Recommended Roadmap Direction

**Do:** Deploy the service, accumulate baseline, observe real drift detection.

**Do:** Fix topology attribution as the first code change — it affects the quality
of every output downstream (recommendations, cost intelligence, workflow inference).

**Do not:** Add more analysis phases until the existing pipeline is running
continuously and producing daily outputs. The system has reached functional
completeness — the bottleneck is now operational deployment, not feature coverage.

---

*This report is based on real VPS scan data from 2026-05-17.
Findings reflect the system as deployed, not as designed.*
