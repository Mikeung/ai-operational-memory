#!/usr/bin/env python3
"""Daily report — runs at 02:00 UTC (09:00 GMT+7) via cron.

Aggregates the last 24h of snapshots, sends a Telegram digest,
saves a markdown report, and git commits + pushes the report.

Cron: 0 2 * * *
"""

import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

LOG_FILE = "/var/log/ai-opsmem-daily.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("daily_report")

REPORTS_DAILY_DIR = PROJECT_ROOT / "reports" / "daily"


def _load_env():
    """Load .env from project root into os.environ (minimal parser)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get_24h_snapshots(store):
    """Return snapshots from the past 24 hours."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    # get_temporal_window returns last N days; use 1 day with high max_count
    snapshots = store.get_temporal_window(days=1, max_count=200)
    return snapshots


def _aggregate_stats(snapshots: list) -> dict:
    """Derive aggregate stats from a list of snapshot dicts."""
    if not snapshots:
        return {
            "scan_count": 0,
            "targets": [],
            "total_workflows": 0,
            "total_recommendations": 0,
            "drift_events": 0,
            "providers": set(),
            "top_recommendations": [],
        }

    targets = set()
    total_workflows = 0
    total_recs = 0
    drift_events = 0
    providers: set[str] = set()
    rec_texts: list[str] = []

    for snap in snapshots:
        data = snap.get("data", {}) if isinstance(snap, dict) else {}
        target = data.get("target", "unknown")
        targets.add(target)

        workflows = data.get("workflows", [])
        total_workflows += len(workflows)

        recs = data.get("recommendations", [])
        total_recs += len(recs)
        for r in recs[:2]:
            text = r.get("title") or r.get("message") or str(r)
            if text and text not in rec_texts:
                rec_texts.append(text)

        drift = data.get("drift")
        if drift and isinstance(drift, dict) and drift.get("change_count", 0) > 0:
            drift_events += 1

        for det in data.get("llm_detections", []):
            p = det.get("provider")
            if p:
                providers.add(p)

    return {
        "scan_count": len(snapshots),
        "targets": sorted(targets),
        "total_workflows": total_workflows,
        "total_recommendations": total_recs,
        "drift_events": drift_events,
        "providers": providers,
        "top_recommendations": rec_texts[:3],
    }


def _build_markdown_report(stats: dict, generated_at: str, snapshot_count: int) -> str:
    lines = [
        f"# Daily Operational Report",
        f"Generated: {generated_at}",
        "",
        "## Summary (last 24h)",
        "",
        f"- Scans completed: **{stats['scan_count']}**",
        f"- Targets covered: {', '.join(stats['targets']) or 'none'}",
        f"- Inferred workflows: {stats['total_workflows']}",
        f"- Recommendations generated: {stats['total_recommendations']}",
        f"- Drift events detected: {stats['drift_events']}",
        f"- LLM providers seen: {', '.join(sorted(stats['providers'])) or 'none'}",
        f"- Total stored snapshots: {snapshot_count}",
        "",
    ]

    if stats["top_recommendations"]:
        lines.append("## Top Recommendations")
        lines.append("")
        for rec in stats["top_recommendations"]:
            lines.append(f"- {rec}")
        lines.append("")

    lines += [
        "---",
        "",
        "*Advisory only — operational decisions require human review.*",
    ]
    return "\n".join(lines)


def _save_report(content: str, date_str: str) -> Path:
    REPORTS_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DAILY_DIR / f"{date_str}_daily_report.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def _git_commit_and_push(report_path: Path, date_str: str) -> bool:
    """Commit the daily report and push to remote."""
    rel_path = report_path.relative_to(PROJECT_ROOT)
    try:
        subprocess.run(
            ["git", "add", str(rel_path)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        commit_msg = f"daily report {date_str} [automated]"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        log.info("Git commit: %s", result.stdout.strip())

        push_result = subprocess.run(
            ["git", "push"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        log.info("Git push: %s", push_result.stdout.strip() or "ok")
        return True
    except subprocess.CalledProcessError as exc:
        log.error("Git operation failed: %s\n%s", exc, exc.stderr)
        return False


def _send_telegram(stats: dict, snapshot_count: int) -> bool:
    _load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    enabled = os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true"

    if not enabled or not token or not chat_id:
        log.info("Telegram disabled or unconfigured — skipping delivery")
        return False

    try:
        from delivery.formatting import format_daily_digest
        from delivery.telegram import TelegramDeliveryClient

        digest = format_daily_digest(
            system_status="ok" if stats["scan_count"] > 0 else "degraded",
            scan_count=stats["scan_count"],
            snapshot_count=snapshot_count,
            max_snapshot_count=10000,
            top_recommendations=stats["top_recommendations"] or None,
            active_recommendation_count=stats["total_recommendations"],
            storage_status="ok",
            disk_pct=0.0,
            scheduler_status="ok",
            scheduler_job_count=2,
        )

        client = TelegramDeliveryClient(token=token, chat_id=chat_id)
        result = client.send_digest(digest)

        if result.success:
            log.info("Telegram digest sent successfully")
        else:
            log.warning("Telegram delivery failed: %s", result.error)
        return result.success

    except Exception as exc:
        log.error("Telegram send error: %s", exc, exc_info=True)
        return False


def main():
    generated_at = datetime.now(UTC).isoformat()
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    log.info("=== Daily report starting — %s ===", generated_at)

    _load_env()

    try:
        from memory.snapshot_engine import SnapshotEngine
        from memory.store import OperationalStore

        db_path = PROJECT_ROOT / "data" / "operational_memory.db"
        store = OperationalStore(str(db_path))
        store.connect()
        engine = SnapshotEngine(store)

        snapshots = engine.get_temporal_window(days=1, max_count=200)
        snapshot_count = store.count_snapshots()
        log.info("Loaded %d snapshots from last 24h (total: %d)", len(snapshots), snapshot_count)

    except Exception as exc:
        log.error("Failed to load snapshots: %s", exc, exc_info=True)
        snapshots = []
        snapshot_count = 0

    stats = _aggregate_stats(snapshots)
    log.info(
        "Stats: %d scans, %d targets, %d workflows, %d recs, %d drift events",
        stats["scan_count"],
        len(stats["targets"]),
        stats["total_workflows"],
        stats["total_recommendations"],
        stats["drift_events"],
    )

    report_content = _build_markdown_report(stats, generated_at, snapshot_count)
    report_path = _save_report(report_content, date_str)
    log.info("Report saved: %s", report_path)

    pushed = _git_commit_and_push(report_path, date_str)
    if not pushed:
        log.warning("Git push failed — report saved locally but not pushed")

    sent = _send_telegram(stats, snapshot_count)

    log.info(
        "=== Daily report complete — telegram=%s git_push=%s ===",
        "ok" if sent else "fail",
        "ok" if pushed else "fail",
    )


if __name__ == "__main__":
    main()
