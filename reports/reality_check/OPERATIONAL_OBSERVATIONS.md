# Operational Observations
Reality Check — First Real VPS Deployment
2026-05-17

Tone: skeptical. Evidence-oriented. Not marketing.

---

## System Context

- VPS: Ubuntu 6.8.0, 39-day uptime, 150GB disk (45% used), 15.6GB RAM
- Active Python services: 6 (lesia, seo-agent, dtv-agent, unknown×2, docker-proxied)
- Scan targets used: /root/ai-operational-memory, /root/telegram-humint, /root/mempalace
- Scan mode: direct (not daemonized)
- Telegram delivery: verified, 5 messages sent, 0 failures

---

## Report Usefulness

### What produced value

**Workflow inference is the strongest signal.** TELEGRAM_LLM_PIPELINE at 0.88
confidence for telegram-humint is accurate and would be non-obvious to someone
approaching the codebase cold. API_LLM_WRAPPER and MULTI_PROVIDER_ORCHESTRATION
for ai-operational-memory are also correct. This is the feature that would
actually help a new operator understand a codebase quickly.

**Scan speed is excellent.** 0.6–1.15s per full scan (repo + process + service +
runtime + topology + workflow + recommendations). On a VPS with 6 running services,
this is operationally viable for 5-minute intervals.

**Telegram delivery is clean.** Messages are readable on mobile. The daily digest
format answers "what's running" in <400 chars. The critical alert format is
scannable in under 10 seconds. Quiet-hour and duplicate suppression work correctly.

**SQLite is appropriate.** 53 KB for 4 snapshots. Negligible overhead. No
fragmentation. At projected steady-state (30-day retention, 3 targets at 5-min
intervals), the DB should remain under 100 MB.

### What produced noise or weak signal

**Recommendations are generic and repeat across targets.** The same 3–4
recommendations fired for both ai-operational-memory and telegram-humint despite
them being structurally different projects. "No vector store detected alongside
LLM usage" is technically true but not actionable for most projects. "Add
request-level latency tracking" is a reasonable suggestion but fires on every
LLM-using codebase regardless of whether observability already exists.

**Priority field is null on all recommendations.** Every recommendation came back
with `priority: null`. This is a data gap — the UI or report consumer cannot
sort by urgency without this field. Operators would need to infer priority from
confidence score alone.

**Runtime health score is always 1.00.** Three different project types, all
returning `runtime_health: healthy, score: 1.0`. This suggests the runtime health
check either has no signals to work with in direct-scan mode or its thresholds
are never triggered. The score is vacuously reassuring rather than informative.

---

## Obvious Noise / False Positives

### Topology pollution — high impact

The topology builder includes ALL VPS services for every target scan. Scanning
`/root/telegram-humint` produces topology nodes for:
- `:5432 (postgresql)` — not used by telegram-humint
- `:6379 (redis)` — not used by telegram-humint
- `:7600 (lesia)` — a completely unrelated service
- `:9200 (elasticsearch)` — not used by telegram-humint
- `:7000 (unknown-7000)` — unknown service, not related

The service scanner reads live port state for the entire system. On a VPS with
multiple co-resident projects, every scan target gets topology nodes for services
it doesn't own. This inflates node counts (28–30 nodes vs. what would be ~5–8
per project) and would generate false workflow inferences and false cost
recommendations on a more saturated VPS.

**Impact:** HIGH. On a VPS with 10+ co-resident projects, topology would become
noise-dominated. The "No vector store detected" recommendation would fire because
it sees Elasticsearch but doesn't attribute it to the correct project.

### "No vector store detected" — medium false positive rate

The recommendation fires because the LLM detector sees OpenAI/Anthropic imports
but no vector store. On this VPS, Elasticsearch IS running (Docker, port 9200).
The recommendation fires anyway because it doesn't know that Elasticsearch belongs
to a different project. This is a topology attribution problem.

### Survivability is vacuously stable

With only 4 snapshots and no baseline, the survivability report correctly says
"stable" but the stability assessment has no information content — it's stable
because there's no history to compare against, not because anything meaningful
was measured. Survivability only becomes meaningful after 7+ days.

---

## Repetitive Alerts

Not yet observable (only 4 snapshots). Expected pattern after steady-state:
- "No vector store detected alongside LLM usage" will fire on every scan of
  every LLM-using project — daily digests would include it repeatedly
- "Add request-level latency tracking" — same pattern

Both are candidates for early deduplication/suppression.

---

## Operational Blind Spots

**Per-project isolation is missing.** There is no mechanism to attribute a running
service or port to a specific project. A scan of any directory sees the same
service landscape. This limits the topology's utility for multi-project VPS
environments (which is this VPS's actual state).

**No historical baseline yet.** All temporal analysis (drift, trend, regression)
requires multiple snapshots across time. The system cannot detect "this project
changed" or "token costs are rising" with only 4 snapshots. The useful half of
the system's intelligence is dormant until a baseline accumulates.

**Scheduler is not daemonized.** The service has no systemd unit. Periodic scans
do not run. The daily Telegram digest will not fire. This is the most operationally
significant gap for real-world use.

**Port 8000 conflict.** dtv-agent occupies port 8000. ai-operational-memory
would need a different port (8080 or 9100 suggested) if deployed as an API service.

---

## Storage Behavior

- Current: 53 KB for 4 snapshots (~13 KB/snapshot average)
- Each snapshot stores full topology JSON, recommendations, runtime health
- Projected: at 5-min intervals × 3 targets = 864 snapshots/day × 13 KB ≈ 11 MB/day
- With 30-day retention: ~330 MB steady-state — larger than anticipated

**Retention is critical.** Without active retention, the DB would reach 330 MB
in 30 days of full operation. The retention engine exists and is tested but is
not currently scheduled.

---

## Scheduler Behavior

Not running. Not daemonized. For real operational use, two gaps must be closed:
1. A systemd unit file for the API service
2. The service started on a non-conflicting port

Until then, scans can only be triggered manually.

---

## Ingestion Behavior

No LLM events have been ingested. The LLM event store (llm_store.py) is
connected but empty. The SDK adapters exist but are not wired to any active
LLM workflow. Real LLM usage intelligence will only emerge when the operator
connects their active LLM-using projects to the ingestion endpoint.

---

## SQLite Observations

- WAL mode: not verified (default is DELETE journal mode for fresh DB)
- Page size: 4096 bytes (SQLite default)
- Fragmentation: 0 freelist pages (clean)
- Index coverage: snapshots table has basic schema, no explicit indexes observed
- At 13 KB/snapshot, page utilization is efficient

No SQLite performance concerns at current scale.

---

## Scaling Observations

At current state (4 snapshots, 3 targets), there are no scaling pressures.
Projected steady-state (30-day history, 3 targets, 5-min interval):
- ~864 snapshots/day × 30 days = 25,920 snapshots — well within SQLite comfort zone
- DB size ~330 MB — manageable but requires retention discipline
- Scan time: 0.6–1.15s/target × 3 targets = ~3s per scan cycle — fine for 5-min intervals

The topology node count (28–30) growing with VPS service count is the main scaling
concern: a VPS with 20+ services would produce 60–80 node topologies per scan, most
of them unattributed noise.

---

## Operator Ergonomics Observations

**Telegram digest is the right delivery mechanism.** Mobile-readable, fast to scan,
answers the right question ("what matters right now?"). The 3-bullet recommendation
format is appropriate compression.

**The CLI scan could use a --target flag.** Currently the scan target is set via
.env SCAN_TARGETS. Running ad-hoc scans against specific directories requires
editing .env or calling Python directly.

**Reports are markdown-first.** This is correct for an operator who reads in a
terminal or VS Code. However, there is no summary view — the operator must read
each individual report file. A single-line `status` command output would help.

**Advisory language is appropriate but verbose.** Every report ends with
"Advisory only — all operational decisions require human review." This is
correct in spirit but at the 4th repetition it becomes wallpaper. Consider
embedding it once at the top of a session summary rather than in every section.

---

## Summary of Issues Requiring Attention

| Priority | Issue | Impact |
|---|---|---|
| HIGH | Service not daemonized — scheduler not running | Periodic scans not executing |
| HIGH | Topology pollution from VPS-wide service discovery | False positive recommendations |
| HIGH | Priority field null on all recommendations | Cannot sort by urgency |
| MED | Generic recommendations repeat across projects | Alert fatigue |
| MED | Runtime health always 1.0 — no signal | Vacuous health checks |
| MED | Retention not scheduled | DB will grow unbounded |
| LOW | Port 8000 conflict with dtv-agent | Blocks API deployment |
| LOW | "No vector store" fires on Elasticsearch-using VPS | Attribution false positive |

---

*This document is operational — not marketing. All observations are based on
real scan output from this VPS on 2026-05-17.*
