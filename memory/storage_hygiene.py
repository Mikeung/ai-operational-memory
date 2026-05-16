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
