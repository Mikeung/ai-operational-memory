"""
Storage hygiene engine — observe disk and database storage pressure.

Purely observational and advisory. Does NOT delete anything.
Provides storage estimates, pressure classifications, and growth observations.

Pressure levels (based on VPS operational thresholds):
- ok:       below 70% of available disk or below soft limits
- warning:  70-85% disk usage or approaching snapshot limits
- critical: above 85% disk usage or significantly exceeding limits
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Pressure thresholds (fraction of disk used)
_PRESSURE_WARNING = 0.70
_PRESSURE_CRITICAL = 0.85

# Snapshot count soft thresholds relative to max_snapshot_count
_COUNT_WARNING_FRACTION = 0.80   # 80% of max → warning
_COUNT_CRITICAL_FRACTION = 0.95  # 95% of max → critical


@dataclass
class StorageEstimate:
    """Point-in-time storage snapshot."""

    db_size_bytes: int
    db_path: str
    disk_total_bytes: int
    disk_used_bytes: int
    disk_free_bytes: int
    disk_usage_fraction: float
    snapshot_count: int
    max_snapshot_count: int
    snapshot_count_fraction: float
    pressure_level: str  # "ok" | "warning" | "critical"
    observations: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_size_bytes": self.db_size_bytes,
            "db_size_human": _human_bytes(self.db_size_bytes),
            "db_path": self.db_path,
            "disk_total_bytes": self.disk_total_bytes,
            "disk_used_bytes": self.disk_used_bytes,
            "disk_free_bytes": self.disk_free_bytes,
            "disk_free_human": _human_bytes(self.disk_free_bytes),
            "disk_usage_fraction": round(self.disk_usage_fraction, 3),
            "disk_usage_percent": round(self.disk_usage_fraction * 100, 1),
            "snapshot_count": self.snapshot_count,
            "max_snapshot_count": self.max_snapshot_count,
            "snapshot_count_fraction": round(self.snapshot_count_fraction, 3),
            "pressure_level": self.pressure_level,
            "observations": self.observations,
            "generated_at": self.generated_at,
        }


@dataclass
class StorageGrowthObservation:
    """Observed growth trend from comparing two StorageEstimates."""

    db_growth_bytes: int
    snapshot_growth: int
    window_description: str
    observations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_growth_bytes": self.db_growth_bytes,
            "db_growth_human": _human_bytes(abs(self.db_growth_bytes)),
            "snapshot_growth": self.snapshot_growth,
            "window_description": self.window_description,
            "observations": self.observations,
        }


class StorageHygieneEngine:
    """
    Observes storage pressure from disk usage and snapshot counts.

    Reads from the filesystem and the store — never writes, never deletes.
    Operators use these observations to decide whether to run retention.
    """

    def estimate(
        self,
        db_path: str,
        snapshot_count: int,
        max_snapshot_count: int = 200,
    ) -> StorageEstimate:
        """Produce a storage estimate for the current state."""
        db_path_obj = Path(db_path)
        db_size = db_path_obj.stat().st_size if db_path_obj.exists() else 0

        disk = shutil.disk_usage(str(db_path_obj.parent) if db_path_obj.exists() else "/")
        disk_usage_fraction = disk.used / disk.total if disk.total > 0 else 0.0

        count_fraction = snapshot_count / max_snapshot_count if max_snapshot_count > 0 else 0.0

        pressure, observations = self._assess_pressure(
            disk_usage_fraction=disk_usage_fraction,
            count_fraction=count_fraction,
            snapshot_count=snapshot_count,
            max_snapshot_count=max_snapshot_count,
            db_size=db_size,
        )

        logger.info(
            "Storage estimate computed",
            extra={
                "pressure": pressure,
                "disk_pct": round(disk_usage_fraction * 100, 1),
                "snapshot_count": snapshot_count,
            },
        )
        return StorageEstimate(
            db_size_bytes=db_size,
            db_path=str(db_path),
            disk_total_bytes=disk.total,
            disk_used_bytes=disk.used,
            disk_free_bytes=disk.free,
            disk_usage_fraction=disk_usage_fraction,
            snapshot_count=snapshot_count,
            max_snapshot_count=max_snapshot_count,
            snapshot_count_fraction=count_fraction,
            pressure_level=pressure,
            observations=observations,
        )

    def compare(
        self,
        earlier: StorageEstimate,
        later: StorageEstimate,
    ) -> StorageGrowthObservation:
        """Compare two estimates to produce a growth observation."""
        db_growth = later.db_size_bytes - earlier.db_size_bytes
        snap_growth = later.snapshot_count - earlier.snapshot_count

        observations: list[str] = []
        if db_growth > 0:
            observations.append(
                f"Database grew by {_human_bytes(db_growth)} since earlier estimate."
            )
        elif db_growth < 0:
            observations.append(
                f"Database shrank by {_human_bytes(abs(db_growth))} — retention may have run."
            )

        if snap_growth > 0:
            observations.append(f"Snapshot count increased by {snap_growth}.")
        elif snap_growth < 0:
            observations.append(f"Snapshot count decreased by {abs(snap_growth)} — deletions occurred.")

        if not observations:
            observations.append("No significant storage change observed.")

        return StorageGrowthObservation(
            db_growth_bytes=db_growth,
            snapshot_growth=snap_growth,
            window_description=f"{earlier.generated_at} → {later.generated_at}",
            observations=observations,
        )

    def _assess_pressure(
        self,
        disk_usage_fraction: float,
        count_fraction: float,
        snapshot_count: int,
        max_snapshot_count: int,
        db_size: int,
    ) -> tuple[str, list[str]]:
        observations: list[str] = []
        pressure = "ok"

        # Disk pressure
        if disk_usage_fraction >= _PRESSURE_CRITICAL:
            pressure = "critical"
            observations.append(
                f"Disk usage at {disk_usage_fraction:.0%} — critically high. "
                "Consider running retention immediately."
            )
        elif disk_usage_fraction >= _PRESSURE_WARNING:
            pressure = "warning"
            observations.append(
                f"Disk usage at {disk_usage_fraction:.0%} — approaching capacity. "
                "Consider scheduling retention."
            )

        # Snapshot count pressure
        if count_fraction >= _COUNT_CRITICAL_FRACTION:
            if pressure != "critical":
                pressure = "critical"
            observations.append(
                f"Snapshot count {snapshot_count}/{max_snapshot_count} "
                f"({count_fraction:.0%}) — at capacity. Retention recommended."
            )
        elif count_fraction >= _COUNT_WARNING_FRACTION:
            if pressure == "ok":
                pressure = "warning"
            observations.append(
                f"Snapshot count {snapshot_count}/{max_snapshot_count} "
                f"({count_fraction:.0%}) — approaching limit."
            )

        # DB size observation
        if db_size > 500 * 1024 * 1024:  # 500 MB
            observations.append(
                f"Database size {_human_bytes(db_size)} — large for a single-node deployment."
            )
        elif db_size > 100 * 1024 * 1024:  # 100 MB
            observations.append(f"Database size {_human_bytes(db_size)}.")

        if pressure == "ok" and not observations:
            observations.append(
                f"Storage pressure normal. "
                f"Disk: {disk_usage_fraction:.0%} used. "
                f"Snapshots: {snapshot_count}/{max_snapshot_count}."
            )

        return pressure, observations


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n = int(n / 1024)
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# Per-project storage awareness (Phase 10 extension)
# ---------------------------------------------------------------------------

@dataclass
class ProjectStorageProfile:
    """Storage footprint for a single project."""

    project_id: str
    snapshot_count: int
    llm_event_count: int
    total_tokens: int
    estimated_cost: float
    latest_snapshot_at: str | None
    latest_event_at: str | None
    snapshot_share: float   # fraction of total snapshots in DB
    event_share: float      # fraction of total LLM events in DB
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "snapshot_count": self.snapshot_count,
            "llm_event_count": self.llm_event_count,
            "total_tokens": self.total_tokens,
            "estimated_cost": round(self.estimated_cost, 6),
            "latest_snapshot_at": self.latest_snapshot_at,
            "latest_event_at": self.latest_event_at,
            "snapshot_share": round(self.snapshot_share, 4),
            "event_share": round(self.event_share, 4),
            "observations": self.observations,
        }


@dataclass
class ProjectStorageSummary:
    """Cross-project storage distribution."""

    total_snapshots: int
    total_llm_events: int
    project_profiles: list[ProjectStorageProfile]
    runaway_projects: list[str]
    concentration_observations: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_snapshots": self.total_snapshots,
            "total_llm_events": self.total_llm_events,
            "project_count": len(self.project_profiles),
            "project_profiles": [p.to_dict() for p in self.project_profiles],
            "runaway_projects": self.runaway_projects,
            "concentration_observations": self.concentration_observations,
            "generated_at": self.generated_at,
        }


class ProjectStorageHygiene:
    """
    Observes per-project storage usage and flags imbalances.

    Purely observational — never deletes.
    Accepts pre-fetched stats from store queries to avoid cross-module coupling.
    """

    _RUNAWAY_SNAPSHOT_SHARE = 0.70   # single project owning 70%+ of snapshots
    _RUNAWAY_EVENT_SHARE = 0.70      # single project owning 70%+ of events

    def build_project_summary(
        self,
        snapshot_stats: list[dict[str, Any]],
        event_stats: list[dict[str, Any]],
    ) -> ProjectStorageSummary:
        """
        Build per-project storage profiles.

        snapshot_stats: rows from OperationalStore.get_project_snapshot_stats()
        event_stats: rows from LLMEventStore.count_events_by_project()
        """
        total_snapshots = sum(r.get("snapshot_count", 0) or 0 for r in snapshot_stats)
        total_events = sum(r.get("event_count", 0) or 0 for r in event_stats)

        # Index event stats by project
        event_by_project: dict[str, dict[str, Any]] = {
            r["project_id"]: r for r in event_stats if r.get("project_id")
        }

        profiles: list[ProjectStorageProfile] = []

        for snap_row in snapshot_stats:
            pid = str(snap_row.get("project_id") or "")
            if not pid:
                continue

            snap_count = int(snap_row.get("snapshot_count", 0) or 0)
            ev_row = event_by_project.get(pid, {})
            ev_count = int(ev_row.get("event_count", 0) or 0)
            tokens = int(ev_row.get("total_tokens", 0) or 0)
            cost = float(ev_row.get("total_estimated_cost", 0) or 0)

            snap_share = snap_count / max(total_snapshots, 1)
            ev_share = ev_count / max(total_events, 1)

            observations = _project_storage_observations(pid, snap_share, ev_share)

            profiles.append(ProjectStorageProfile(
                project_id=pid,
                snapshot_count=snap_count,
                llm_event_count=ev_count,
                total_tokens=tokens,
                estimated_cost=cost,
                latest_snapshot_at=snap_row.get("latest_at"),
                latest_event_at=ev_row.get("latest_at"),
                snapshot_share=snap_share,
                event_share=ev_share,
                observations=observations,
            ))

        # Also include projects with events but no snapshots
        for pid, ev_row in event_by_project.items():
            if not any(p.project_id == pid for p in profiles):
                ev_count = int(ev_row.get("event_count", 0) or 0)
                tokens = int(ev_row.get("total_tokens", 0) or 0)
                cost = float(ev_row.get("total_estimated_cost", 0) or 0)
                ev_share = ev_count / max(total_events, 1)
                profiles.append(ProjectStorageProfile(
                    project_id=pid,
                    snapshot_count=0,
                    llm_event_count=ev_count,
                    total_tokens=tokens,
                    estimated_cost=cost,
                    latest_snapshot_at=None,
                    latest_event_at=ev_row.get("latest_at"),
                    snapshot_share=0.0,
                    event_share=ev_share,
                    observations=_project_storage_observations(pid, 0.0, ev_share),
                ))

        runaway = [
            p.project_id for p in profiles
            if p.snapshot_share >= self._RUNAWAY_SNAPSHOT_SHARE
            or p.event_share >= self._RUNAWAY_EVENT_SHARE
        ]

        concentration_obs = _concentration_observations(profiles, total_snapshots, total_events)

        logger.info(
            "Project storage summary built",
            extra={
                "project_count": len(profiles),
                "runaway_count": len(runaway),
                "total_snapshots": total_snapshots,
                "total_events": total_events,
            },
        )
        return ProjectStorageSummary(
            total_snapshots=total_snapshots,
            total_llm_events=total_events,
            project_profiles=sorted(profiles, key=lambda p: p.snapshot_count + p.llm_event_count, reverse=True),
            runaway_projects=runaway,
            concentration_observations=concentration_obs,
        )


def _project_storage_observations(
    project_id: str, snap_share: float, ev_share: float
) -> list[str]:
    obs = []
    if snap_share >= 0.70:
        obs.append(
            f"Project '{project_id}' holds {snap_share:.0%} of all snapshots — "
            "disproportionate concentration may indicate missing retention."
        )
    if ev_share >= 0.70:
        obs.append(
            f"Project '{project_id}' holds {ev_share:.0%} of all LLM events — "
            "consider per-project retention to balance storage."
        )
    return obs


def _concentration_observations(
    profiles: list[ProjectStorageProfile],
    total_snapshots: int,
    total_events: int,
) -> list[str]:
    obs = []
    if not profiles:
        return ["No project-scoped data available yet."]

    top_snap = max(profiles, key=lambda p: p.snapshot_share)
    if top_snap.snapshot_share >= 0.70:
        obs.append(
            f"Snapshot concentration: '{top_snap.project_id}' holds {top_snap.snapshot_share:.0%} "
            f"of {total_snapshots:,} total snapshots."
        )

    top_ev = max(profiles, key=lambda p: p.event_share)
    if top_ev.event_share >= 0.70:
        obs.append(
            f"LLM event concentration: '{top_ev.project_id}' holds {top_ev.event_share:.0%} "
            f"of {total_events:,} total events."
        )

    if not obs:
        obs.append(
            f"Storage appears balanced across {len(profiles)} project(s). "
            "No runaway projects detected."
        )

    return obs
