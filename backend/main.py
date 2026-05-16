from fastapi import FastAPI

from backend.config import settings
from backend.health import router as health_router
from backend.lifecycle import lifespan
from backend.routers.ecosystem import router as ecosystem_router
from backend.routers.investigation import router as investigation_router
from backend.routers.reports import router as reports_router
from backend.routers.runtime import router as runtime_router
from backend.routers.scan import router as scan_router
from backend.routers.snapshots import router as snapshots_router
from backend.routers.temporal import router as temporal_router
from backend.routers.topology import router as topology_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Operational intelligence and memory layer for AI agent ecosystems.",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(scan_router)
app.include_router(snapshots_router)
app.include_router(reports_router)
app.include_router(topology_router)
app.include_router(temporal_router)
app.include_router(runtime_router)
app.include_router(investigation_router)
app.include_router(ecosystem_router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "philosophy": "Observe automatically. Decide manually.",
        "endpoints": {
            "health": "GET /health",
            "scan": "POST /scan",
            "scan_status": "GET /scan/status",
            "snapshots": "GET /snapshots",
            "latest_snapshot": "GET /snapshots/latest",
            "latest_report": "GET /reports/latest",
            "topology": "GET /topology/latest",
            "workflows": "GET /topology/workflows",
            "recommendations": "GET /topology/recommendations",
            "topology_report": "GET /topology/report",
            "temporal_analysis": "GET /temporal/analysis",
            "temporal_timeline": "GET /temporal/timeline",
            "temporal_priority": "GET /temporal/priority",
            "temporal_attention": "GET /temporal/attention",
            "temporal_volatility": "GET /temporal/volatility",
            "runtime_health": "GET /runtime/health",
            "runtime_severity": "GET /runtime/severity",
            "runtime_recurrence": "GET /runtime/recurrence",
            "runtime_fused": "GET /runtime/fused",
            "runtime_digest": "GET /runtime/digest",
            "runtime_digest_morning": "GET /runtime/digest/morning",
            "runtime_digest_critical": "GET /runtime/digest/critical",
            "investigate": "GET /investigation/investigate",
            "investigate_report": "GET /investigation/investigate/report",
            "compare": "GET /investigation/compare",
            "compare_report": "GET /investigation/compare/report",
            "continuity": "GET /investigation/continuity",
            "continuity_report": "GET /investigation/continuity/report",
            "patterns": "GET /investigation/patterns",
            "explain_severity": "GET /investigation/explain/severity",
            "explain_recommendation": "GET /investigation/explain/recommendation",
            "evidence_recommendation": "GET /investigation/evidence/recommendation",
            "evidence_severity": "GET /investigation/evidence/severity",
            "persistent_report": "GET /investigation/report/persistent",
            "ecosystem_summary": "GET /ecosystem/summary",
            "ecosystem_themes": "GET /ecosystem/themes",
            "ecosystem_clusters": "GET /ecosystem/clusters",
            "ecosystem_drift": "GET /ecosystem/drift",
            "ecosystem_trends": "GET /ecosystem/trends",
            "ecosystem_review": "GET /ecosystem/review",
            "ecosystem_report_themes": "GET /ecosystem/report/themes",
            "ecosystem_report_concerns": "GET /ecosystem/report/concerns",
            "ecosystem_report_drift": "GET /ecosystem/report/drift",
            "ecosystem_report_complexity": "GET /ecosystem/report/complexity",
            "ecosystem_digest_weekly": "GET /ecosystem/digest/weekly",
            "ecosystem_digest_strategic": "GET /ecosystem/digest/strategic",
        },
    }
