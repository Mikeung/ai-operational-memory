import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OperationalStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()
        logger.info("Database connected", extra={"path": str(self.db_path)})

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database disconnected")

    def _migrate(self) -> None:
        assert self._conn is not None
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS scan_records (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scanner    TEXT    NOT NULL,
                target     TEXT    NOT NULL,
                status     TEXT    NOT NULL DEFAULT 'completed',
                result     TEXT    NOT NULL DEFAULT '{}',
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_type TEXT NOT NULL,
                data          TEXT NOT NULL DEFAULT '{}',
                notes         TEXT NOT NULL DEFAULT '',
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_scan_records_scanner
                ON scan_records(scanner, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_snapshots_type
                ON snapshots(snapshot_type, created_at DESC);
        """)
        self._conn.commit()
        logger.info("Database schema migrated")

    def insert_scan_record(
        self, scanner: str, target: str, result: dict[str, Any], status: str = "completed"
    ) -> int:
        assert self._conn is not None
        cursor = self._conn.execute(
            "INSERT INTO scan_records (scanner, target, status, result) VALUES (?, ?, ?, ?)",
            (scanner, target, status, json.dumps(result)),
        )
        self._conn.commit()
        row_id = cursor.lastrowid or 0
        logger.debug("Scan record inserted", extra={"scanner": scanner, "id": row_id})
        return row_id

    def insert_snapshot(self, snapshot_type: str, data: dict[str, Any], notes: str = "") -> int:
        assert self._conn is not None
        cursor = self._conn.execute(
            "INSERT INTO snapshots (snapshot_type, data, notes) VALUES (?, ?, ?)",
            (snapshot_type, json.dumps(data), notes),
        )
        self._conn.commit()
        row_id = cursor.lastrowid or 0
        logger.debug("Snapshot inserted", extra={"type": snapshot_type, "id": row_id})
        return row_id

    def get_recent_scans(self, scanner: str, limit: int = 10) -> list[dict[str, Any]]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM scan_records WHERE scanner = ? ORDER BY created_at DESC LIMIT ?",
            (scanner, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_snapshot(self, snapshot_type: str) -> dict[str, Any] | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM snapshots WHERE snapshot_type = ? ORDER BY created_at DESC LIMIT 1",
            (snapshot_type,),
        ).fetchone()
        if not row:
            return None
        return _deserialize_snapshot(dict(row))

    def get_snapshot_by_id(self, snapshot_id: int) -> dict[str, Any] | None:
        assert self._conn is not None
        row = self._conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if not row:
            return None
        return _deserialize_snapshot(dict(row))

    def list_snapshots(self, snapshot_type: str | None, limit: int) -> list[dict[str, Any]]:
        assert self._conn is not None
        if snapshot_type:
            rows = self._conn.execute(
                "SELECT * FROM snapshots WHERE snapshot_type = ? ORDER BY created_at DESC LIMIT ?",
                (snapshot_type, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM snapshots ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_deserialize_snapshot(dict(r)) for r in rows]

    def get_snapshots_in_window(
        self, snapshot_type: str, days: int, max_count: int = 50
    ) -> list[dict[str, Any]]:
        """Return snapshots from the last N days, oldest first, for temporal analysis."""
        assert self._conn is not None
        rows = self._conn.execute(
            """SELECT * FROM snapshots
               WHERE snapshot_type = ?
                 AND created_at >= datetime('now', ? || ' days')
               ORDER BY created_at ASC
               LIMIT ?""",
            (snapshot_type, f"-{days}", max_count),
        ).fetchall()
        return [_deserialize_snapshot(dict(r)) for r in rows]

    def count_snapshots(self, snapshot_type: str | None = None) -> int:
        """Return the total number of stored snapshots, optionally filtered by type."""
        assert self._conn is not None
        if snapshot_type:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM snapshots WHERE snapshot_type = ?",
                (snapshot_type,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()
        return int(row[0]) if row else 0

    def delete_snapshots_by_ids(self, snapshot_ids: list[int]) -> int:
        """Delete snapshots by ID list. Returns the number of rows deleted.

        Never called automatically — only invoked by explicit operator action
        via RetentionEngine.execute() with dry_run=False.
        """
        assert self._conn is not None
        if not snapshot_ids:
            return 0
        placeholders = ",".join("?" * len(snapshot_ids))
        cursor = self._conn.execute(
            f"DELETE FROM snapshots WHERE id IN ({placeholders})",
            snapshot_ids,
        )
        self._conn.commit()
        deleted = cursor.rowcount
        logger.info("Snapshots deleted", extra={"count": deleted, "ids": snapshot_ids})
        return deleted

    def get_db_size_bytes(self) -> int:
        """Return the size of the SQLite database file in bytes."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0


def _deserialize_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    if "data" in row and isinstance(row["data"], str):
        try:
            row["data"] = json.loads(row["data"])
        except (json.JSONDecodeError, ValueError):
            pass
    return row
