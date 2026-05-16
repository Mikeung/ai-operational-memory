import logging
from typing import Any

from memory.store import OperationalStore

logger = logging.getLogger(__name__)


class SnapshotEngine:
    """Creates, stores, and retrieves operational snapshots.

    Snapshots are immutable once written. History is append-only.
    The engine never modifies existing records.
    """

    def __init__(self, store: OperationalStore) -> None:
        self._store = store

    def create_snapshot(
        self,
        data: dict[str, Any],
        snapshot_type: str = "full_scan",
        notes: str = "",
    ) -> int:
        snapshot_id = self._store.insert_snapshot(snapshot_type, data, notes)
        logger.info(
            "Snapshot created",
            extra={"id": snapshot_id, "type": snapshot_type},
        )
        return snapshot_id

    def get_latest(self, snapshot_type: str = "full_scan") -> dict[str, Any] | None:
        return self._store.get_latest_snapshot(snapshot_type)

    def get_by_id(self, snapshot_id: int) -> dict[str, Any] | None:
        return self._store.get_snapshot_by_id(snapshot_id)

    def list_recent(
        self, snapshot_type: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        return self._store.list_snapshots(snapshot_type, limit)

    def get_temporal_window(
        self, days: int = 7, max_count: int = 50
    ) -> list[dict[str, Any]]:
        """Return full_scan snapshots from the last N days, oldest first."""
        return self._store.get_snapshots_in_window("full_scan", days, max_count)
