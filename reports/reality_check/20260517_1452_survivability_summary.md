# Survivability Summary
Generated: 2026-05-17 14:52 UTC

## Overall: OK — Long-term outlook: STABLE

Checked against current VPS state (4 snapshots, 39-day uptime system).

| Check | Status |
|---|---|
| DB growth | OK — DB at 53KB, no growth pressure |
| Retention backlog | OK — 4 snapshots, no cleanup needed |
| Scheduler degradation | N/A — not running as daemon |
| Stale archives | OK — no archived projects |
| Ingestion pressure | OK — no LLM events ingested |
| Delivery health | OK — 2 successes, 0 failures |

## Constraints

- No 7-day DB growth baseline available (insufficient history)
- Scheduler check is vacuously OK (scheduler not started)
- Survivability is most useful after 7+ days of continuous operation

## Long-Term Indicators (projected)

At 5-minute scan intervals across 3 targets, the DB would grow by roughly
1-2 KB/snapshot × 864 daily snapshots = ~1-2 MB/day. At 30-day retention,
steady-state DB size would be approximately 30-60 MB — well within the
SQLite comfortable range for this workload.

---
*Advisory only. All decisions require operator review.*
