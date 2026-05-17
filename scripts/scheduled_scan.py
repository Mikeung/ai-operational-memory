#!/usr/bin/env python3
"""Scheduled scan — runs every 6 hours via cron.

Scans all configured VPS targets, stores snapshots, logs results.
Cron: 0 0,6,12,18 * * *
"""

import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on sys.path when invoked from cron
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

LOG_FILE = "/var/log/ai-opsmem-scan.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("scheduled_scan")

SCAN_TARGETS = [
    "/root/ai-operational-memory",
    "/root/telegram-humint",
    "/root/mempalace",
    "/root/projects/lesia",
    "/root/seo-agent",
]


def build_dependencies():
    from memory.drift_detector import DriftDetector
    from memory.snapshot_engine import SnapshotEngine
    from memory.store import OperationalStore
    from reports.generator import ReportGenerator
    from scanners.process_scanner import ProcessScanner
    from scanners.registry import ScannerRegistry
    from scanners.repo_scanner import RepoScanner
    from scanners.runtime_scanner import RuntimeScanner
    from scanners.service_scanner import ServiceScanner

    store = OperationalStore(str(PROJECT_ROOT / "data" / "operational_memory.db"))
    store.connect()
    snapshot_engine = SnapshotEngine(store)
    drift_detector = DriftDetector()
    report_generator = ReportGenerator(output_dir=str(PROJECT_ROOT / "data" / "reports"))

    registry = ScannerRegistry()
    registry.register(RepoScanner())
    registry.register(ProcessScanner())
    registry.register(ServiceScanner())
    registry.register(RuntimeScanner())

    return registry, snapshot_engine, drift_detector, report_generator


def scan_target(target: str, registry, snapshot_engine, drift_detector, report_generator):
    from backend.operations import run_full_scan

    if not Path(target).exists():
        log.warning("Target does not exist, skipping: %s", target)
        return None

    t0 = time.monotonic()
    try:
        result = run_full_scan(
            target=target,
            registry=registry,
            snapshot_engine=snapshot_engine,
            drift_detector=drift_detector,
            report_generator=report_generator,
        )
        duration = round(time.monotonic() - t0, 3)
        log.info(
            "Scan complete: %s | snapshot=%s | nodes=%s | workflows=%s | recs=%s | drift=%s | %.2fs",
            target,
            result["snapshot_id"],
            result["topology"]["node_count"],
            len(result["workflows"]),
            len(result["recommendations"]),
            result["drift"]["change_count"] if result["drift"] else 0,
            duration,
        )
        return result
    except Exception as exc:
        log.error("Scan failed for %s: %s", target, exc, exc_info=True)
        return None


def main():
    started_at = datetime.now(UTC).isoformat()
    log.info("=== Scheduled scan starting — %s ===", started_at)

    try:
        registry, snapshot_engine, drift_detector, report_generator = build_dependencies()
    except Exception as exc:
        log.error("Failed to initialise scan dependencies: %s", exc, exc_info=True)
        sys.exit(1)

    results = []
    for target in SCAN_TARGETS:
        result = scan_target(target, registry, snapshot_engine, drift_detector, report_generator)
        results.append((target, result))

    successful = sum(1 for _, r in results if r is not None)
    failed = len(results) - successful
    log.info(
        "=== Scan cycle complete — %d/%d targets succeeded ===",
        successful,
        len(results),
    )
    if failed:
        log.warning("%d target(s) failed", failed)


if __name__ == "__main__":
    main()
