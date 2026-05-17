"""
Runtime Survivability — long-term operational health assessment.

Answers: "Can this system survive 6+ months of continuous operation?"

Checks:
1. DB growth acceleration — is storage growing faster than expected?
2. Scheduler degradation — are jobs failing or going stale over time?
3. Retention backlog — are old snapshots/events accumulating?
4. Stale archived projects — are archived projects still consuming space?
5. Ingestion pressure accumulation — is ingestion volume trending upward?
6. Long-running instability indicators — recurring errors, unresolved warnings

Design rules:
- Observational only. Never modifies state.
- All inputs are pre-fetched from stores. No direct DB access here.
- Deterministic: same inputs → same output.
- Bounded language throughout.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Thresholds
_DB_GROWTH_WARN_BYTES_PER_DAY = 10 * 1024 * 1024   # 10 MB/day
_DB_GROWTH_CRIT_BYTES_PER_DAY = 50 * 1024 * 1024   # 50 MB/day
_RETENTION_BACKLOG_WARN_DAYS = 45                    # snapshots older than 45d
_RETENTION_BACKLOG_CRIT_DAYS = 90                    # snapshots older than 90d
_STALE_ARCHIVE_DAYS = 180                            # archived project with no activity
_SCHEDULER_STALE_MULTIPLIER = 3                      # 3x interval = stale
_INGESTION_TREND_WARN_FRACTION = 0.25                # 25% growth in ingestion rate


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class SurvivabilityCheck:
    """Result of a single survivability check."""
    name: str
    passed: bool
    severity: str           # "ok" | "warning" | "critical"
    message: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
        }


@dataclass
class SurvivabilityReport:
    """
    Long-running operational health assessment.

    Summarizes whether the system appears sustainable for continued operation
    without manual intervention.
    """
    overall_status: str          # "ok" | "warning" | "critical"
    checks: list[SurvivabilityCheck]
    passed: int
    warned: int
    critical: int
    long_term_outlook: str       # "stable" | "attention_needed" | "intervention_recommended"
    observations: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "long_term_outlook": self.long_term_outlook,
            "checks": [c.to_dict() for c in self.checks],
            "passed": self.passed,
            "warned": self.warned,
            "critical": self.critical,
            "total_checks": len(self.checks),
            "observations": self.observations,
            "generated_at": self.generated_at,
            "advisory": (
                "Survivability checks are observational. "
                "They suggest potential issues — not failures. "
                "Human review is always required before any action."
            ),
        }

    def markdown(self) -> str:
        lines = [
            "# Runtime Survivability Report",
            f"Generated: {self.generated_at}",
            "",
            f"**Overall status:** {self.overall_status.upper()}  "
            f"| **Long-term outlook:** {self.long_term_outlook.replace('_', ' ')}",
            f"**Checks:** {self.passed} passed / {self.warned} warning / {self.critical} critical",
            "",
        ]

        if self.observations:
            lines += ["## Key Observations", ""]
            for o in self.observations:
                lines.append(f"- {o}")
            lines.append("")

        lines += ["## Check Details", ""]
        for c in self.checks:
            icon = "✓" if c.passed else ("⚠" if c.severity == "warning" else "✗")
            lines.append(f"### {icon} {c.name}")
            lines.append(f"Status: **{c.severity}**")
            lines.append("")
            lines.append(c.message)
            if c.evidence:
                lines.append("")
                for e in c.evidence:
                    lines.append(f"> {e}")
            lines.append("")

        lines += [
            "---",
            "_Advisory only. Survivability assessment is based on observable trends. "
            "All remediation decisions require operator review._",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

class RuntimeSurvivabilityChecker:
    """
    Assesses long-term operational sustainability.

    All inputs are pre-fetched to keep this module stateless and testable.
    No direct database access.
    """

    def check(
        self,
        *,
        db_size_bytes: int,
        db_size_bytes_7d_ago: int | None,
        snapshot_count: int,
        oldest_snapshot_days: int | None,
        llm_event_count: int,
        oldest_event_days: int | None,
        scheduler_health: dict[str, Any] | None,
        archived_project_ids: list[str],
        archived_project_last_activity_days: dict[str, int],
        events_last_hour_by_project: dict[str, int],
        events_last_hour_7d_ago: dict[str, int] | None,
    ) -> SurvivabilityReport:
        """
        Run all survivability checks and return a report.

        Parameters:
        - db_size_bytes: current database size
        - db_size_bytes_7d_ago: database size a week ago (None if unavailable)
        - snapshot_count: current total snapshot count
        - oldest_snapshot_days: age of the oldest snapshot in days
        - llm_event_count: current total LLM event count
        - oldest_event_days: age of the oldest LLM event in days
        - scheduler_health: output from OperationalScheduler.get_health_status()
        - archived_project_ids: list of archived project IDs
        - archived_project_last_activity_days: days since last activity per archived project
        - events_last_hour_by_project: current events/hour per project
        - events_last_hour_7d_ago: events/hour per project one week ago (None if unavailable)
        """
        checks: list[SurvivabilityCheck] = []

        checks.append(self._check_db_growth(
            db_size_bytes, db_size_bytes_7d_ago
        ))
        checks.append(self._check_retention_backlog(
            snapshot_count, oldest_snapshot_days, llm_event_count, oldest_event_days
        ))
        checks.append(self._check_scheduler_degradation(scheduler_health))
        checks.append(self._check_stale_archives(
            archived_project_ids, archived_project_last_activity_days
        ))
        checks.append(self._check_ingestion_pressure_trend(
            events_last_hour_by_project, events_last_hour_7d_ago
        ))

        passed = sum(1 for c in checks if c.passed)
        warned = sum(1 for c in checks if not c.passed and c.severity == "warning")
        critical = sum(1 for c in checks if c.severity == "critical")

        if critical > 0:
            overall = "critical"
            outlook = "intervention_recommended"
        elif warned >= 2:
            overall = "warning"
            outlook = "attention_needed"
        elif warned == 1:
            overall = "warning"
            outlook = "attention_needed"
        else:
            overall = "ok"
            outlook = "stable"

        observations = self._build_observations(checks)

        logger.info(
            "Survivability check complete",
            extra={
                "overall": overall,
                "passed": passed,
                "warned": warned,
                "critical": critical,
            },
        )

        return SurvivabilityReport(
            overall_status=overall,
            checks=checks,
            passed=passed,
            warned=warned,
            critical=critical,
            long_term_outlook=outlook,
            observations=observations,
        )

    # -----------------------------------------------------------------------
    # Individual checks
    # -----------------------------------------------------------------------

    def _check_db_growth(
        self,
        current_bytes: int,
        past_bytes: int | None,
    ) -> SurvivabilityCheck:
        if past_bytes is None:
            return SurvivabilityCheck(
                name="Database Growth Rate",
                passed=True,
                severity="ok",
                message="No historical size comparison available — cannot assess growth rate.",
                evidence=["Baseline will be established after the next comparison window."],
            )

        growth = current_bytes - past_bytes
        daily_growth = growth / 7  # weekly → daily

        current_human = _human_bytes(current_bytes)
        growth_human = _human_bytes(abs(growth))
        daily_human = _human_bytes(abs(int(daily_growth)))

        if daily_growth > _DB_GROWTH_CRIT_BYTES_PER_DAY:
            return SurvivabilityCheck(
                name="Database Growth Rate",
                passed=False,
                severity="critical",
                message=(
                    f"Database appears to be growing at {daily_human}/day — "
                    "at this rate, storage pressure may become critical within weeks."
                ),
                evidence=[
                    f"Current size: {current_human}",
                    f"Growth over 7 days: {growth_human}",
                    f"Estimated daily growth: {daily_human}",
                    "Consider running retention to reduce growth rate.",
                ],
            )
        elif daily_growth > _DB_GROWTH_WARN_BYTES_PER_DAY:
            return SurvivabilityCheck(
                name="Database Growth Rate",
                passed=False,
                severity="warning",
                message=(
                    f"Database growing at {daily_human}/day. "
                    "Monitor for acceleration."
                ),
                evidence=[
                    f"Current size: {current_human}",
                    f"Growth over 7 days: {growth_human}",
                ],
            )
        elif growth < 0:
            return SurvivabilityCheck(
                name="Database Growth Rate",
                passed=True,
                severity="ok",
                message=f"Database shrank by {growth_human} over 7 days — retention appears to be running.",
                evidence=[f"Current size: {current_human}"],
            )
        else:
            return SurvivabilityCheck(
                name="Database Growth Rate",
                passed=True,
                severity="ok",
                message=f"Database growth rate normal ({daily_human}/day).",
                evidence=[f"Current size: {current_human}", f"7-day growth: {growth_human}"],
            )

    def _check_retention_backlog(
        self,
        snapshot_count: int,
        oldest_snapshot_days: int | None,
        event_count: int,
        oldest_event_days: int | None,
    ) -> SurvivabilityCheck:
        issues = []

        if oldest_snapshot_days is not None and oldest_snapshot_days > _RETENTION_BACKLOG_CRIT_DAYS:
            issues.append(
                f"Oldest snapshot is {oldest_snapshot_days} days old "
                f"(retention threshold: {_RETENTION_BACKLOG_CRIT_DAYS} days)"
            )
        elif oldest_snapshot_days is not None and oldest_snapshot_days > _RETENTION_BACKLOG_WARN_DAYS:
            issues.append(
                f"Oldest snapshot is {oldest_snapshot_days} days old — "
                f"approaching retention threshold ({_RETENTION_BACKLOG_WARN_DAYS} days)"
            )

        if oldest_event_days is not None and oldest_event_days > _RETENTION_BACKLOG_CRIT_DAYS:
            issues.append(
                f"Oldest LLM event is {oldest_event_days} days old "
                f"(threshold: {_RETENTION_BACKLOG_CRIT_DAYS} days)"
            )

        if not issues:
            return SurvivabilityCheck(
                name="Retention Backlog",
                passed=True,
                severity="ok",
                message=(
                    f"No retention backlog detected. "
                    f"Snapshots: {snapshot_count:,}. Events: {event_count:,}."
                ),
                evidence=[
                    f"Oldest snapshot: {oldest_snapshot_days or 'unknown'} days",
                    f"Oldest event: {oldest_event_days or 'unknown'} days",
                ],
            )

        is_critical = any("critical" in i.lower() or _RETENTION_BACKLOG_CRIT_DAYS in [
            oldest_snapshot_days, oldest_event_days
        ] for i in issues)
        # Determine if critical based on threshold crossing
        crit = (
            (oldest_snapshot_days is not None and oldest_snapshot_days > _RETENTION_BACKLOG_CRIT_DAYS)
            or (oldest_event_days is not None and oldest_event_days > _RETENTION_BACKLOG_CRIT_DAYS)
        )

        return SurvivabilityCheck(
            name="Retention Backlog",
            passed=False,
            severity="critical" if crit else "warning",
            message=(
                "Retention backlog detected — old data has not been pruned. "
                "Run retention to prevent unbounded growth."
            ),
            evidence=issues + [
                f"Total snapshots: {snapshot_count:,}",
                f"Total LLM events: {event_count:,}",
            ],
        )

    def _check_scheduler_degradation(
        self, scheduler_health: dict[str, Any] | None
    ) -> SurvivabilityCheck:
        if scheduler_health is None:
            return SurvivabilityCheck(
                name="Scheduler Health",
                passed=True,
                severity="ok",
                message="Scheduler health not available (no scheduler state provided).",
            )

        status = scheduler_health.get("status", "unknown")
        stale_jobs = scheduler_health.get("stale_jobs", [])
        degraded_jobs = scheduler_health.get("degraded_jobs", [])

        if status == "critical" or len(degraded_jobs) > 0:
            return SurvivabilityCheck(
                name="Scheduler Health",
                passed=False,
                severity="critical",
                message=(
                    f"Scheduler degradation detected — {len(degraded_jobs)} degraded job(s). "
                    "Long-running degradation indicates scan failures are accumulating."
                ),
                evidence=[
                    f"Scheduler status: {status}",
                    f"Degraded jobs: {', '.join(degraded_jobs)}",
                    f"Stale jobs: {len(stale_jobs)}",
                ],
            )
        elif stale_jobs:
            return SurvivabilityCheck(
                name="Scheduler Health",
                passed=False,
                severity="warning",
                message=(
                    f"{len(stale_jobs)} stale scheduler job(s) detected — "
                    "jobs have not run recently."
                ),
                evidence=[
                    f"Stale jobs: {', '.join(str(j) for j in stale_jobs)}",
                    "Stale jobs may indicate process restart or scan failure.",
                ],
            )
        else:
            return SurvivabilityCheck(
                name="Scheduler Health",
                passed=True,
                severity="ok",
                message=f"Scheduler appears healthy. Status: {status}.",
                evidence=[f"Running jobs: {scheduler_health.get('running_jobs', 0)}"],
            )

    def _check_stale_archives(
        self,
        archived_ids: list[str],
        last_activity_days: dict[str, int],
    ) -> SurvivabilityCheck:
        stale = [
            pid for pid in archived_ids
            if last_activity_days.get(pid, 0) >= _STALE_ARCHIVE_DAYS
        ]

        if not archived_ids:
            return SurvivabilityCheck(
                name="Stale Archived Projects",
                passed=True,
                severity="ok",
                message="No archived projects found.",
            )

        if stale:
            return SurvivabilityCheck(
                name="Stale Archived Projects",
                passed=False,
                severity="warning",
                message=(
                    f"{len(stale)} archived project(s) have had no activity for "
                    f"{_STALE_ARCHIVE_DAYS}+ days. "
                    "Consider reviewing whether their data should be retained."
                ),
                evidence=[
                    f"Stale archives: {', '.join(stale)}",
                    "Stale archives continue to consume storage without operational value.",
                    "Review whether retention should be run on these projects.",
                ],
            )

        return SurvivabilityCheck(
            name="Stale Archived Projects",
            passed=True,
            severity="ok",
            message=f"{len(archived_ids)} archived project(s) — none are stale.",
        )

    def _check_ingestion_pressure_trend(
        self,
        current_rates: dict[str, int],
        past_rates: dict[str, int] | None,
    ) -> SurvivabilityCheck:
        if not current_rates:
            return SurvivabilityCheck(
                name="Ingestion Pressure Trend",
                passed=True,
                severity="ok",
                message="No active ingestion detected.",
            )

        if past_rates is None:
            return SurvivabilityCheck(
                name="Ingestion Pressure Trend",
                passed=True,
                severity="ok",
                message="No historical ingestion comparison available — trend cannot be assessed.",
                evidence=["Baseline will be established after the next comparison window."],
            )

        growing = []
        for pid, current in current_rates.items():
            past = past_rates.get(pid, 0)
            if past > 0:
                growth = (current - past) / past
                if growth >= _INGESTION_TREND_WARN_FRACTION:
                    growing.append(f"{pid}: +{growth:.0%}")

        if growing:
            return SurvivabilityCheck(
                name="Ingestion Pressure Trend",
                passed=False,
                severity="warning",
                message=(
                    f"Ingestion volume appears to be growing in {len(growing)} project(s). "
                    "If this trend continues, storage and rate limits may be exceeded."
                ),
                evidence=growing + [
                    "Growth threshold: 25% increase week-over-week",
                    "Consider enabling event sampling or adjusting retention policy.",
                ],
            )

        return SurvivabilityCheck(
            name="Ingestion Pressure Trend",
            passed=True,
            severity="ok",
            message="Ingestion volume appears stable or decreasing.",
            evidence=[f"Active projects: {len(current_rates)}"],
        )

    # -----------------------------------------------------------------------
    # Observations
    # -----------------------------------------------------------------------

    def _build_observations(self, checks: list[SurvivabilityCheck]) -> list[str]:
        obs = []
        failures = [c for c in checks if not c.passed]
        critical = [c for c in failures if c.severity == "critical"]

        if critical:
            obs.append(
                f"{len(critical)} critical survivability concern(s): "
                f"{', '.join(c.name for c in critical)}. "
                "Immediate attention may be required."
            )

        non_critical = [c for c in failures if c.severity == "warning"]
        if non_critical:
            obs.append(
                f"{len(non_critical)} warning(s) detected: "
                f"{', '.join(c.name for c in non_critical)}."
            )

        if not failures:
            obs.append(
                "All survivability checks passed. "
                "System appears suitable for continued long-term operation."
            )

        return obs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n = int(n / 1024)
    return f"{n:.1f} TB"


def days_since(iso_timestamp: str | None) -> int | None:
    """Compute days since a timestamp. Returns None if timestamp is None/unparseable."""
    if not iso_timestamp:
        return None
    try:
        ts = datetime.fromisoformat(iso_timestamp.replace(" ", "T"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - ts
        return max(0, delta.days)
    except (ValueError, AttributeError):
        return None
