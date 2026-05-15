import logging
import time
from datetime import UTC, datetime
from typing import Any

from llm_intelligence.detector import LLMDetector
from memory.drift_detector import DriftDetector
from memory.snapshot_engine import SnapshotEngine
from reports.generator import ReportGenerator
from scanners.registry import ScannerRegistry

logger = logging.getLogger(__name__)


def run_full_scan(
    target: str,
    registry: ScannerRegistry,
    snapshot_engine: SnapshotEngine,
    drift_detector: DriftDetector,
    report_generator: ReportGenerator,
) -> dict[str, Any]:
    t0 = time.monotonic()
    logger.info("Full scan starting", extra={"target": target})

    scan_output = registry.run_all(target)
    llm_result = LLMDetector().scan_directory(target)

    payload: dict[str, Any] = {
        "target": target,
        "scanned_at": datetime.now(UTC).isoformat(),
        "scanner_results": scan_output,
        "llm_detections": llm_result,
    }

    previous = snapshot_engine.get_latest("full_scan")
    snapshot_id = snapshot_engine.create_snapshot(payload, "full_scan")

    drift: dict[str, Any] | None = None
    drift_report: str | None = None

    if previous:
        prev_id = previous.get("id", 0)
        drift = drift_detector.compare(previous.get("data", {}), payload)
        if drift["change_count"] > 0:
            drift_report = report_generator.drift_report(drift, prev_id, snapshot_id)
        logger.info(
            "Drift detection complete",
            extra={"change_count": drift["change_count"], "target": target},
        )

    snapshot_report = report_generator.snapshot_report({"data": payload}, snapshot_id)

    duration = round(time.monotonic() - t0, 3)
    payload["duration_s"] = duration

    result: dict[str, Any] = {
        "snapshot_id": snapshot_id,
        "target": target,
        "scan_output": scan_output,
        "llm_detections": llm_result,
        "drift": drift,
        "snapshot_report": snapshot_report,
        "drift_report": drift_report,
        "duration_s": duration,
    }

    logger.info(
        "Full scan complete",
        extra={
            "snapshot_id": snapshot_id,
            "target": target,
            "duration_s": duration,
            "drift_changes": drift["change_count"] if drift else 0,
            "llm_providers": [d["provider"] for d in llm_result],
        },
    )
    return result
