"""
Telegram message formatting — compact, mobile-readable, operationally actionable.

Each format function answers: "What matters right now?"

Uses Telegram HTML parse mode.
All output is bounded to < 4096 chars (Telegram limit).
No raw JSON. No markdown walls. No evidence dumps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_MAX_LEN = 4000   # leave headroom below 4096 for safety
_TRUNCATION_NOTICE = "\n\n<i>(truncated — see full report)</i>"


# ---------------------------------------------------------------------------
# Daily digest
# ---------------------------------------------------------------------------

def format_daily_digest(
    *,
    system_status: str,
    scan_count: int,
    snapshot_count: int,
    max_snapshot_count: int,
    top_recommendations: list[str] | None = None,
    active_recommendation_count: int = 0,
    storage_status: str = "ok",
    disk_pct: float = 0.0,
    scheduler_status: str = "ok",
    scheduler_job_count: int = 0,
    generated_at: str | None = None,
) -> str:
    ts = generated_at or _now()
    status_icon = _status_icon(system_status)
    snap_pct = (snapshot_count / max_snapshot_count * 100) if max_snapshot_count > 0 else 0.0

    lines = [
        f"<b>Daily Operational Digest</b>",
        f"{ts}",
        "",
        f"{status_icon} <b>System:</b> {system_status.upper()}",
        f"<b>Scans today:</b> {scan_count}",
        f"<b>Snapshots:</b> {snapshot_count}/{max_snapshot_count} ({snap_pct:.0f}%)",
    ]

    if top_recommendations:
        lines.append("")
        lines.append(f"<b>Recommendations ({active_recommendation_count} active):</b>")
        for rec in top_recommendations[:3]:
            lines.append(f"• {_escape(rec)}")

    lines += [
        "",
        f"<b>Storage:</b> {disk_pct:.0f}% disk used ({storage_status})",
        f"<b>Scheduler:</b> {scheduler_job_count} job(s), {scheduler_status}",
    ]

    return _finalize("\n".join(lines))


# ---------------------------------------------------------------------------
# Critical alert
# ---------------------------------------------------------------------------

def format_critical_alert(
    *,
    kind: str,
    summary: str,
    confidence: float = 0.0,
    evidence: list[str] | None = None,
    generated_at: str | None = None,
) -> str:
    ts = generated_at or _now()
    lines = [
        f"🚨 <b>CRITICAL: {_escape(kind)}</b>",
        f"{ts}",
        "",
        _escape(summary),
    ]

    if confidence > 0.0:
        lines.append(f"\n<b>Confidence:</b> {confidence:.0%}")

    if evidence:
        lines.append("")
        lines.append("<b>Evidence:</b>")
        for ev in evidence[:3]:
            lines.append(f"• {_escape(ev)}")

    lines += [
        "",
        "<i>Action required — review and decide manually.</i>",
    ]

    return _finalize("\n".join(lines))


# ---------------------------------------------------------------------------
# Weekly digest
# ---------------------------------------------------------------------------

def format_weekly_digest(
    *,
    scan_count_7d: int,
    active_concern_count: int,
    resolved_count: int,
    new_count: int,
    top_concerns: list[str] | None = None,
    system_status: str = "ok",
    generated_at: str | None = None,
) -> str:
    ts = generated_at or _now()
    status_icon = _status_icon(system_status)

    lines = [
        f"<b>Weekly Operational Digest</b>",
        f"{ts}",
        "",
        f"{status_icon} <b>System:</b> {system_status.upper()}",
        f"<b>Scans this week:</b> {scan_count_7d}",
        f"<b>Active concerns:</b> {active_concern_count} "
        f"(+{new_count} new, {resolved_count} resolved)",
    ]

    if top_concerns:
        lines.append("")
        lines.append("<b>Top concerns:</b>")
        for concern in top_concerns[:4]:
            lines.append(f"• {_escape(concern)}")

    lines += [
        "",
        "<i>Advisory only — all decisions require human review.</i>",
    ]

    return _finalize("\n".join(lines))


# ---------------------------------------------------------------------------
# Survivability warning
# ---------------------------------------------------------------------------

def format_survivability_warning(
    *,
    outlook: str,
    warning_checks: list[str],
    critical_checks: list[str] | None = None,
    generated_at: str | None = None,
) -> str:
    ts = generated_at or _now()
    icon = "🚨" if critical_checks else "⚠️"

    lines = [
        f"{icon} <b>Survivability Warning</b>",
        f"{ts}",
        f"<b>Long-term outlook:</b> {_escape(outlook.replace('_', ' '))}",
        "",
    ]

    if critical_checks:
        lines.append("<b>Critical issues:</b>")
        for check in critical_checks[:3]:
            lines.append(f"• {_escape(check)}")
        lines.append("")

    if warning_checks:
        lines.append("<b>Warnings:</b>")
        for check in warning_checks[:4]:
            lines.append(f"• {_escape(check)}")
        lines.append("")

    lines.append("<i>Review before next maintenance window.</i>")

    return _finalize("\n".join(lines))


# ---------------------------------------------------------------------------
# Storage pressure warning
# ---------------------------------------------------------------------------

def format_storage_pressure_warning(
    *,
    pressure_level: str,
    disk_pct: float,
    db_size_human: str = "?",
    snapshot_count: int = 0,
    max_snapshot_count: int = 0,
    observations: list[str] | None = None,
    generated_at: str | None = None,
) -> str:
    ts = generated_at or _now()
    icon = "🚨" if pressure_level == "critical" else "⚠️"
    snap_info = (
        f"{snapshot_count}/{max_snapshot_count}"
        if max_snapshot_count > 0
        else str(snapshot_count)
    )

    lines = [
        f"{icon} <b>Storage Pressure: {pressure_level.upper()}</b>",
        f"{ts}",
        "",
        f"<b>Disk:</b> {disk_pct:.0f}% used",
        f"<b>DB size:</b> {_escape(db_size_human)}",
        f"<b>Snapshots:</b> {snap_info}",
    ]

    if observations:
        lines.append("")
        lines.append("<b>Notes:</b>")
        for obs in observations[:3]:
            lines.append(f"• {_escape(obs)}")

    lines += [
        "",
        "<i>Consider running retention to free space.</i>",
    ]

    return _finalize("\n".join(lines))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _status_icon(status: str) -> str:
    return {"ok": "✅", "warning": "⚠️", "critical": "🚨"}.get(status.lower(), "ℹ️")


def _escape(text: str) -> str:
    """Escape HTML special chars for Telegram HTML mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _finalize(text: str) -> str:
    """Ensure the message fits within Telegram's limit."""
    if len(text) <= _MAX_LEN:
        return text
    cut = _MAX_LEN - len(_TRUNCATION_NOTICE)
    return text[:cut] + _TRUNCATION_NOTICE
