"""
Recurring issue detection — chronic operational concern tracking.

Analyzes snapshot history to identify patterns that repeat:
- repeated recommendation categories
- recurring cost warnings
- unstable workflow patterns
- repeated drift of the same components
- recurring runtime failures

Repeated problems matter more than isolated ones.
Recurrence elevates severity and operator attention priority.

Deterministic. Evidence-backed. No speculation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_MIN_OCCURRENCES = 2
_TITLE_KEY_LEN = 60
_OBS_KEY_LEN = 70


@dataclass
class RecurringIssue:
    """An operational concern that appeared in multiple snapshots."""
    kind: str            # "recommendation", "cost_warning", "drift", "runtime_failure"
    pattern: str         # normalized description of what recurs
    occurrences: int
    snapshot_ids: list[int]
    first_seen: str
    last_seen: str
    evidence: list[str]
    severity_hint: str   # "low", "moderate", "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "pattern": self.pattern,
            "occurrences": self.occurrences,
            "snapshot_ids": self.snapshot_ids,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "evidence": self.evidence,
            "severity_hint": self.severity_hint,
        }


class RecurrenceEngine:
    """Detects chronic operational concerns from snapshot history.

    Compares patterns across snapshots rather than just N vs N-1.
    Uses string-prefix matching for recommendations and cost observations
    to group semantically similar issues across scans.
    """

    def detect(self, snapshots: list[dict[str, Any]]) -> list[RecurringIssue]:
        """Detect recurring patterns across all provided snapshots.

        snapshots: list of snapshot dicts, any order (oldest or newest first).
        Each snapshot has: id, created_at, data.
        """
        if len(snapshots) < _MIN_OCCURRENCES:
            logger.info(
                "Recurrence detection skipped — insufficient snapshots",
                extra={"snapshot_count": len(snapshots)},
            )
            return []

        issues: list[RecurringIssue] = []
        issues.extend(self._detect_recommendation_recurrence(snapshots))
        issues.extend(self._detect_cost_warning_recurrence(snapshots))
        issues.extend(self._detect_drift_recurrence(snapshots))
        issues.extend(self._detect_runtime_failure_recurrence(snapshots))

        issues.sort(key=lambda x: -x.occurrences)

        logger.info(
            "Recurrence detection complete",
            extra={
                "snapshot_count": len(snapshots),
                "recurring_issues": len(issues),
            },
        )
        return issues

    def _detect_recommendation_recurrence(
        self, snapshots: list[dict[str, Any]]
    ) -> list[RecurringIssue]:
        pattern_map: dict[str, list[tuple[int, str]]] = {}

        for snap in snapshots:
            snap_id = snap.get("id", 0)
            created_at = snap.get("created_at", "")
            recs = snap.get("data", {}).get("recommendations", [])
            for rec in recs:
                key = _rec_key(rec)
                if key:
                    pattern_map.setdefault(key, []).append((snap_id, created_at))

        return [
            RecurringIssue(
                kind="recommendation",
                pattern=key,
                occurrences=len(appearances),
                snapshot_ids=[a[0] for a in appearances],
                first_seen=min(a[1] for a in appearances),
                last_seen=max(a[1] for a in appearances),
                evidence=[
                    f"Recommendation '{key}' appeared in {len(appearances)} of {len(snapshots)} scans",
                    f"Snapshot IDs: {[a[0] for a in appearances]}",
                ],
                severity_hint=_recurrence_severity(len(appearances), len(snapshots)),
            )
            for key, appearances in pattern_map.items()
            if len(appearances) >= _MIN_OCCURRENCES
        ]

    def _detect_cost_warning_recurrence(
        self, snapshots: list[dict[str, Any]]
    ) -> list[RecurringIssue]:
        pattern_map: dict[str, list[tuple[int, str]]] = {}

        for snap in snapshots:
            snap_id = snap.get("id", 0)
            created_at = snap.get("created_at", "")
            obs_list = snap.get("data", {}).get("cost_observations", [])
            for obs in obs_list:
                if obs.get("severity") in ("high", "warning"):
                    key = obs.get("observation", "")[:_OBS_KEY_LEN].strip()
                    if key:
                        pattern_map.setdefault(key, []).append((snap_id, created_at))

        return [
            RecurringIssue(
                kind="cost_warning",
                pattern=key,
                occurrences=len(appearances),
                snapshot_ids=[a[0] for a in appearances],
                first_seen=min(a[1] for a in appearances),
                last_seen=max(a[1] for a in appearances),
                evidence=[
                    f"Cost warning '{key[:60]}...' recurred in {len(appearances)} scans",
                    "Recurring cost risk — pattern is structurally embedded, not a transient anomaly",
                ],
                severity_hint=_recurrence_severity(len(appearances), len(snapshots)),
            )
            for key, appearances in pattern_map.items()
            if len(appearances) >= _MIN_OCCURRENCES
        ]

    def _detect_drift_recurrence(
        self, snapshots: list[dict[str, Any]]
    ) -> list[RecurringIssue]:
        """Detect components that drift repeatedly (added/removed multiple times)."""
        from cognition.temporal_analysis import _compare_snapshots

        sorted_snaps = sorted(snapshots, key=lambda s: s.get("created_at", ""))
        component_changes: dict[str, list[tuple[int, str, str]]] = {}

        for i in range(1, len(sorted_snaps)):
            events = _compare_snapshots(sorted_snaps[i - 1], sorted_snaps[i])
            snap_id = sorted_snaps[i].get("id", 0)
            detected_at = sorted_snaps[i].get("created_at", "")
            for ev in events:
                key = ev.value
                component_changes.setdefault(key, []).append((snap_id, detected_at, ev.change_type))

        issues = []
        for component, occurrences in component_changes.items():
            if len(occurrences) >= _MIN_OCCURRENCES:
                snap_ids = [o[0] for o in occurrences]
                issues.append(RecurringIssue(
                    kind="drift",
                    pattern=f"Component '{component}' changed repeatedly",
                    occurrences=len(occurrences),
                    snapshot_ids=snap_ids,
                    first_seen=min(o[1] for o in occurrences),
                    last_seen=max(o[1] for o in occurrences),
                    evidence=[
                        f"'{component}' changed {len(occurrences)} times: "
                        f"{', '.join(o[2] for o in occurrences)}",
                        "Repeated changes indicate instability or active migration",
                    ],
                    severity_hint=_recurrence_severity(len(occurrences), len(sorted_snaps)),
                ))
        return issues

    def _detect_runtime_failure_recurrence(
        self, snapshots: list[dict[str, Any]]
    ) -> list[RecurringIssue]:
        """Detect recurring failed services from runtime scanner data."""
        service_failures: dict[str, list[tuple[int, str]]] = {}

        for snap in snapshots:
            snap_id = snap.get("id", 0)
            created_at = snap.get("created_at", "")
            runtime = snap.get("data", {}).get("scanner_results", {}).get("results", {}).get(
                "runtime_scanner", {}
            )
            for svc in runtime.get("failed_services", []):
                service_failures.setdefault(svc, []).append((snap_id, created_at))

            # Also check runtime_health if stored
            runtime_health = snap.get("data", {}).get("runtime_health", {})
            for svc in runtime_health.get("failed_services", []):
                existing = service_failures.setdefault(svc, [])
                if not any(e[0] == snap_id for e in existing):
                    existing.append((snap_id, created_at))

        return [
            RecurringIssue(
                kind="runtime_failure",
                pattern=f"Service '{svc}' repeatedly failing",
                occurrences=len(appearances),
                snapshot_ids=[a[0] for a in appearances],
                first_seen=min(a[1] for a in appearances),
                last_seen=max(a[1] for a in appearances),
                evidence=[
                    f"Service '{svc}' in failed state across {len(appearances)} scans",
                    "Persistent service failure requires investigation",
                ],
                severity_hint="high" if len(appearances) >= 3 else "moderate",
            )
            for svc, appearances in service_failures.items()
            if len(appearances) >= _MIN_OCCURRENCES
        ]


def _rec_key(rec: dict[str, Any]) -> str:
    title = rec.get("title", "")
    category = rec.get("category", "")
    return f"[{category}] {title[:_TITLE_KEY_LEN]}".strip()


def _recurrence_severity(occurrences: int, total_snapshots: int) -> str:
    ratio = occurrences / max(total_snapshots, 1)
    if ratio >= 0.7 or occurrences >= 5:
        return "high"
    if ratio >= 0.4 or occurrences >= 3:
        return "moderate"
    return "low"
