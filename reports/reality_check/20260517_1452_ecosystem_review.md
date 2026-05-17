# Ecosystem Review Report
Generated: 2026-05-17 14:52 UTC
Scans: 3 targets | Runtime: VPS (39-day uptime, Ubuntu 6.8.0)

## VPS Overview

| Metric | Value |
|---|---|
| Disk usage | 45.3% (67/149 GB) |
| RAM usage | 7.2/15.6 GB (46%) |
| CPU load avg | 0.33 (15-min avg) |
| System uptime | 39 days |
| Python services | 6 active |

## Services Detected (all VPS)

| Port | Service | Status |
|---|---|---|
| 7600 | lesia (uvicorn) | Running |
| 8001 | unknown-8001 (uvicorn) | Running |
| 7500 | seo-agent | Running |
| 7000 | unknown-7000 | Running |
| 7501 | unknown-7501 | Running |
| 8000 | dtv-agent (uvicorn, localhost) | Running |
| 5432 | PostgreSQL | Running |
| 6379 | Redis (Docker) | Running |
| 9200 | Elasticsearch (Docker) | Running |
| 80/443 | nginx | Running |
| 3000 | Docker service (localhost) | Running |
| 3100 | Next.js | Running |

## Target Scan Results

### /root/ai-operational-memory
- **Topology nodes:** 30 (includes VPS-wide service discovery — see observations)
- **Inferred workflows:** API_LLM_WRAPPER (0.80), SCHEDULED_LLM_JOB (0.75), MULTI_PROVIDER_ORCHESTRATION (0.82)
- **Recommendations:** 4 (observability x2, cost x1, topology x1)
- **Runtime health:** 1.00 (healthy)
- **Scan time:** 1.15s

### /root/telegram-humint
- **Topology nodes:** 28
- **Inferred workflows:** TELEGRAM_LLM_PIPELINE (0.88), API_LLM_WRAPPER (0.80), SCHEDULED_LLM_JOB (0.75)
- **Recommendations:** 3 (same pattern as above — see observations)
- **Runtime health:** 1.00 (healthy)
- **Scan time:** 0.80s

### /root/mempalace
- **Topology nodes:** 25
- **Inferred workflows:** 0
- **Recommendations:** 0
- **Scan time:** 0.62s

## LLM Stack Detected

Across VPS: `anthropic`, `openai`, `apscheduler`, `fastapi`, `telegram`

## Notable Topology Finding

The topology includes ALL running VPS services for every target scan.
The service scanner reads live port state system-wide, not per-target.
This causes topology pollution: scanning /telegram-humint produces
nodes for Redis, PostgreSQL, nginx, etc. See observations for implications.

---
*Advisory only. All decisions require operator review.*
