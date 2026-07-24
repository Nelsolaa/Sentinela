import json
import sqlite3
from pathlib import Path
from typing import Any


class AgentQueueCapacityError(RuntimeError):
    pass


class AgentQueue:
    def __init__(self, database_path: str, max_items: int) -> None:
        if max_items <= 0:
            raise ValueError("Agent queue capacity must be greater than zero.")

        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

        self._max_items = max_items
        self._connection = sqlite3.connect(str(Path(database_path).expanduser()))
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.commit()

    def enqueue(self, payload: dict[str, Any]) -> int:
        if self.size() >= self._max_items:
            raise AgentQueueCapacityError("Agent queue capacity reached.")

        serialized = json.dumps(
            payload,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        cursor = self._connection.execute(
            "INSERT INTO pending_metrics (payload) VALUES (?)",
            (serialized,),
        )
        self._connection.commit()
        return int(cursor.lastrowid)

    def pending(self, limit: int) -> list[tuple[int, dict[str, Any]]]:
        if limit <= 0:
            raise ValueError("Queue read limit must be greater than zero.")

        rows = self._connection.execute(
            "SELECT id, payload FROM pending_metrics ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        return [(int(row[0]), json.loads(row[1])) for row in rows]

    def acknowledge(self, item_id: int) -> None:
        self._connection.execute(
            "DELETE FROM pending_metrics WHERE id = ?",
            (item_id,),
        )
        self._connection.commit()

    def size(self) -> int:
        row = self._connection.execute(
            "SELECT COUNT(*) FROM pending_metrics"
        ).fetchone()
        return int(row[0])

    def close(self) -> None:
        self._connection.close()
