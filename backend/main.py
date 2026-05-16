from fastapi import FastAPI

from backend.config import settings
from backend.health import router as health_router
from backend.lifecycle import lifespan
from backend.routers.reports import router as reports_router
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
        },
    }
