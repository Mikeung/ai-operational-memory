import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import settings
from backend.operations import run_full_scan
from backend.scheduler import OperationalScheduler
from memory.drift_detector import DriftDetector
from memory.snapshot_engine import SnapshotEngine
from memory.store import OperationalStore
from observability.logger import setup_logging
from reports.generator import ReportGenerator
from scanners.process_scanner import ProcessScanner
from scanners.registry import ScannerRegistry
from scanners.repo_scanner import RepoScanner
from scanners.service_scanner import ServiceScanner

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)

    logger.info(
        "Application starting",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "debug": settings.debug,
        },
    )

    _ensure_dirs()

    # Storage
    store = OperationalStore(settings.db_path)
    store.connect()
    app.state.store = store

    # Operational components
    snapshot_engine = SnapshotEngine(store)
    drift_detector = DriftDetector()
    report_generator = ReportGenerator(output_dir=settings.reports_dir)

    app.state.snapshot_engine = snapshot_engine
    app.state.drift_detector = drift_detector
    app.state.report_generator = report_generator

    # Scanner registry
    registry = ScannerRegistry()
    registry.register(RepoScanner())
    registry.register(ProcessScanner())
    registry.register(ServiceScanner())
    app.state.registry = registry

    # Scheduler
    targets = [t.strip() for t in settings.scan_targets.split(",") if t.strip()]

    def _scheduled_scan(target: str) -> None:
        try:
            run_full_scan(
                target=target,
                registry=registry,
                snapshot_engine=snapshot_engine,
                drift_detector=drift_detector,
                report_generator=report_generator,
            )
        except Exception as exc:
            logger.error(
                "Scheduled scan failed",
                extra={"target": target, "error": str(exc)},
            )

    scheduler = OperationalScheduler()
    scheduler.register_scan(_scheduled_scan, targets, settings.scan_interval_seconds)
    scheduler.start()
    app.state.scheduler = scheduler

    logger.info(
        "Application ready",
        extra={
            "scan_targets": targets,
            "scan_interval_s": settings.scan_interval_seconds,
            "scanners": registry.registered,
        },
    )

    yield

    logger.info("Application shutting down")
    scheduler.stop()
    store.disconnect()
    logger.info("Application stopped cleanly")


def _ensure_dirs() -> None:
    for path in [os.path.dirname(settings.db_path), settings.reports_dir]:
        if path and not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.info("Created directory", extra={"path": path})
