"""
Operational digest generation.

Produces concise, human-readable digests from multi-source intelligence:
- daily digest: full operational picture from latest snapshot
- morning digest: trend-focused summary for start-of-day review
- critical digest: immediate-action items only, for urgent situations

All output is advisory-only. Read-only reconstruction.
No autonomous decisions. No infrastructure modifications.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_daily_digest(
    snapshot: dict[str, Any],
    runtime_health: dict[str, Any] | None = None,
    attention_report: dict[str, Any] | None = None,
    recurring_issues: list[dict[str, Any]] | None = None,
    severity: dict[str, Any] | None = None,
    fused_insights: list[dict[str, Any]] | None = None,
) -> str:
    """Generate a full daily operational digest.

    Combines snapshot data, runtime health, attention guidance,
    recurring issues, and severity assessment into a single markdown report.
    """
    now = _now()
    snap_id = snapshot.get("id", "?")
    snap_at = snapshot.get("created_at", "unknown")[:16]
    data = snapshot.get("data", {})

    lines: list[str] = [
        "# Daily Operational Digest",
        f"**Generated:** {now}",
        f"**Snapshot:** #{snap_id} ({snap_at} UTC)",
        "",
    ]

    # Severity banner
    if severity:
        level = severity.get("level", "unknown")
        score = severity.get("score", 0.0)
        confidence = severity.get("confidence", 0.0)
        banner = _severity_banner(level)
        lines += [
            f"## {banner} Operational Severity: {level.upper()}",
            f"Score: {score:.3f} | Confidence: {confidence:.2f}",
            "",
        ]
        sev_evidence = severity.get("evidence", [])
        if sev_evidence:
            for ev in sev_evidence:
                lines.append(f"- {ev}")
            lines.append("")

    # Attention summary
    if attention_report:
        summary = attention_report.get("attention_summary", "")
        if summary:
            lines += [
                "## Attention Summary",
                f"> {summary}",
                "",
            ]

        top_concerns = attention_report.get("top_concerns", [])
        if top_concerns:
            lines += ["### Top Concerns", ""]
            for item in top_concerns[:5]:
                urgency = item.get("urgency", "low").upper()
                title = item.get("title", "?")
                summary_text = item.get("summary", "")
                lines.append(f"**[{urgency}]** {title}")
                if summary_text:
                    lines.append(f"  {summary_text}")
            lines.append("")

        runtime_concerns = attention_report.get("runtime_concerns", [])
        if runtime_concerns:
            lines += ["### Runtime Concerns", ""]
            for item in runtime_concerns[:3]:
                urgency = item.get("urgency", "low").upper()
                lines.append(f"**[{urgency}]** {item.get('title', '?')}")
                lines.append(f"  {item.get('summary', '')}")
            lines.append("")

    # Runtime health
    if runtime_health:
        overall = runtime_health.get("overall_status", "unknown")
        hscore = runtime_health.get("health_score", 0.0)
        lines += [
            "## Runtime Health",
            f"**Status:** {overall} | **Score:** {hscore:.3f}",
            "",
        ]
        resource_pressure = runtime_health.get("resource_pressure", [])
        if resource_pressure:
            lines.append("**Resource pressure:**")
            for rp in resource_pressure:
                lines.append(f"- {rp}")
            lines.append("")
        instability = runtime_health.get("instability_signals", [])
        if instability:
            lines.append("**Instability signals:**")
            for sig in instability:
                lines.append(f"- {sig}")
            lines.append("")

    # Topology snapshot
    topology = data.get("topology", {})
    if topology:
        lines += [
            "## Infrastructure Snapshot",
            f"- Nodes: {topology.get('node_count', 0)}",
            f"- Edges: {topology.get('edge_count', 0)}",
            "",
        ]

    workflows = data.get("workflows", [])
    if workflows:
        wf_names = [w.get("name", w.get("workflow_type", "?")) for w in workflows]
        lines += [
            "## Active Workflow Patterns",
            ", ".join(wf_names),
            "",
        ]

    # Cost observations
    cost_obs = data.get("cost_observations", [])
    high_cost = [c for c in cost_obs if c.get("severity") in ("high", "warning")]
    if high_cost:
        lines += ["## Cost Risks", ""]
        for obs in high_cost[:4]:
            lines.append(f"- **[{obs.get('severity', '?').upper()}]** {obs.get('observation', '?')}")
        lines.append("")

    # Fused insights
    if fused_insights:
        lines += ["## Compound Operational Concerns", ""]
        for insight in fused_insights[:4]:
            sev = insight.get("severity", "?")
            lines.append(f"- **[{sev.upper()}]** {insight.get('title', '?')}")
            lines.append(f"  {insight.get('description', '')[:120]}...")
        lines.append("")

    # Recurring issues
    if recurring_issues:
        lines += ["## Recurring Issues", ""]
        for issue in recurring_issues[:5]:
            hint = issue.get("severity_hint", "?")
            pattern = issue.get("pattern", "?")
            occurrences = issue.get("occurrences", 0)
            lines.append(f"- **[{hint.upper()}]** {pattern} ({occurrences}x)")
        lines.append("")

    lines += [
        "---",
        "*Advisory only — all operational decisions require human review.*",
        "*Generated by AI Operational Memory — Observe automatically. Decide manually.*",
    ]

    logger.info("Daily digest generated", extra={"snapshot_id": snap_id})
    return "\n".join(lines)


def generate_morning_digest(
    snapshots: list[dict[str, Any]],
    temporal: dict[str, Any] | None = None,
    attention_report: dict[str, Any] | None = None,
) -> str:
    """Generate a morning start-of-day digest focused on trends and attention.

    Designed to be read quickly before the work day begins.
    Surfaces: what changed overnight, what's volatile, what needs attention.
    """
    now = _now()
    snap_count = len(snapshots)
    latest_snap = snapshots[-1] if snapshots else {}
    latest_id = latest_snap.get("id", "?")

    lines: list[str] = [
        "# Morning Operational Digest",
        f"**Generated:** {now}",
        f"**Snapshots in history:** {snap_count} | **Latest:** #{latest_id}",
        "",
    ]

    if not snapshots:
        lines += ["_No snapshot history available._", ""]
        return "\n".join(lines)

    # Trend summary
    if temporal:
        volatility = temporal.get("volatility_score", 0.0)
        stability = temporal.get("stability_score", 1.0)
        total_changes = temporal.get("total_changes", 0)
        window_days = temporal.get("window_days", 7)

        trend_label = _trend_label(volatility)
        lines += [
            "## Infrastructure Trend",
            f"**{window_days}-day window:** {trend_label}",
            f"- Volatility: {volatility:.2f} | Stability: {stability:.2f}",
            f"- Changes detected: {total_changes}",
            "",
        ]

        churn = temporal.get("churn_indicators", [])
        if churn:
            lines.append("**Churn indicators:**")
            for ind in churn[:3]:
                lines.append(f"- {ind}")
            lines.append("")

        trend_obs = temporal.get("trend_observations", [])
        if trend_obs:
            lines.append("**Trend observations:**")
            for obs in trend_obs[:3]:
                lines.append(f"- {obs}")
            lines.append("")

    # Attention guidance
    if attention_report:
        summary = attention_report.get("attention_summary", "")
        if summary:
            lines += [
                "## What Needs Your Attention",
                f"> {summary}",
                "",
            ]

        top = attention_report.get("top_concerns", [])
        if top:
            lines += ["**Priority concerns:**", ""]
            for item in top[:3]:
                urgency = item.get("urgency", "low").upper()
                title = item.get("title", "?")
                lines.append(f"- **[{urgency}]** {title}")
            lines.append("")

    # Recent activity from latest snapshot
    data = latest_snap.get("data", {})
    recs = data.get("recommendations", [])
    if recs:
        high_recs = [r for r in recs if r.get("impact") == "high"]
        if high_recs:
            lines += ["## High-Impact Recommendations", ""]
            for rec in high_recs[:3]:
                lines.append(f"- {rec.get('title', '?')}: {rec.get('summary', '')[:80]}...")
            lines.append("")

    lines += [
        "---",
        "*Advisory only — all operational decisions require human review.*",
        "*Generated by AI Operational Memory — Observe automatically. Decide manually.*",
    ]

    logger.info(
        "Morning digest generated",
        extra={"snapshot_count": snap_count, "latest_snapshot_id": latest_id},
    )
    return "\n".join(lines)


def generate_critical_digest(
    severity: dict[str, Any],
    attention_report: dict[str, Any] | None = None,
    fused_insights: list[dict[str, Any]] | None = None,
    runtime_health: dict[str, Any] | None = None,
) -> str:
    """Generate a critical-only digest for urgent operational situations.

    Only surfaces critical and high-severity items.
    Designed for immediate-action scenarios.
    """
    now = _now()
    level = severity.get("level", "unknown")
    score = severity.get("score", 0.0)

    lines: list[str] = [
        "# CRITICAL OPERATIONAL DIGEST",
        f"**Generated:** {now}",
        f"**Severity:** {level.upper()} (score: {score:.3f})",
        "",
        "> **This digest surfaces only critical and high-severity operational concerns.**",
        "> **Human review and decision required before any action.**",
        "",
    ]

    # Severity evidence
    sev_evidence = severity.get("evidence", [])
    if sev_evidence:
        lines += ["## Severity Evidence", ""]
        for ev in sev_evidence:
            lines.append(f"- {ev}")
        lines.append("")

        factors = severity.get("factors", [])
        if factors:
            lines += ["**Score breakdown:**", ""]
            for f in factors:
                name = f.get("name", "?")
                contribution = f.get("contribution", 0.0)
                desc = f.get("description", "")
                if contribution > 0.05:
                    lines.append(f"- {name}: {contribution:.3f} — {desc}")
            lines.append("")

    # Runtime health
    if runtime_health and runtime_health.get("overall_status") in ("stressed", "critical"):
        lines += [
            "## Runtime Status",
            f"**{runtime_health['overall_status'].upper()}** — score: {runtime_health.get('health_score', 0.0):.3f}",
            "",
        ]
        for sig in runtime_health.get("instability_signals", [])[:4]:
            lines.append(f"- {sig}")
        for rp in runtime_health.get("resource_pressure", [])[:4]:
            lines.append(f"- {rp}")
        lines.append("")

    # Critical + high attention items
    if attention_report:
        top = attention_report.get("top_concerns", [])
        critical_items = [i for i in top if i.get("urgency") in ("critical", "high")]
        if critical_items:
            lines += ["## Immediate Concerns", ""]
            for item in critical_items:
                urgency = item.get("urgency", "?").upper()
                lines.append(f"### [{urgency}] {item.get('title', '?')}")
                lines.append(item.get("summary", ""))
                for ev in item.get("evidence", [])[:2]:
                    lines.append(f"  - {ev}")
                lines.append("")

        runtime_concerns = attention_report.get("runtime_concerns", [])
        if runtime_concerns:
            lines += ["## Runtime Concerns", ""]
            for item in runtime_concerns:
                urgency = item.get("urgency", "?").upper()
                lines.append(f"- **[{urgency}]** {item.get('title', '?')}: {item.get('summary', '')}")
            lines.append("")

    # High/critical fused insights
    if fused_insights:
        severe_fused = [i for i in fused_insights if i.get("severity") in ("critical", "high")]
        if severe_fused:
            lines += ["## Compound Risks", ""]
            for insight in severe_fused:
                sev = insight.get("severity", "?").upper()
                lines.append(f"### [{sev}] {insight.get('title', '?')}")
                lines.append(insight.get("description", ""))
                for ev in insight.get("evidence", [])[:3]:
                    lines.append(f"- {ev}")
                lines.append("")

    lines += [
        "---",
        "**ADVISORY ONLY — no automated action has been taken.**",
        "**All operational decisions require human review and authorization.**",
        "*Generated by AI Operational Memory — Observe automatically. Decide manually.*",
    ]

    logger.info(
        "Critical digest generated",
        extra={"severity_level": level, "severity_score": score},
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _severity_banner(level: str) -> str:
    banners = {
        "critical": "🔴",
        "high": "🟠",
        "moderate": "🟡",
        "low": "🔵",
        "informational": "⚪",
    }
    return banners.get(level, "⚪")


def _trend_label(volatility: float) -> str:
    if volatility >= 0.7:
        return "HIGH VOLATILITY — infrastructure is churning rapidly"
    if volatility >= 0.45:
        return "Elevated volatility — moderate infrastructure churn"
    if volatility >= 0.2:
        return "Low volatility — minor changes detected"
    return "Stable — minimal infrastructure change"
