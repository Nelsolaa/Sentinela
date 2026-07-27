from datetime import datetime, timezone
from typing import Any


def normalize_timestamp(value: Any | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, datetime):
        timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat()

    timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return timestamp.astimezone(timezone.utc).isoformat()


def prepare_metric(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "measurement": payload.get("measurement", "system_metrics"),
        "tags": payload.get("tags") or {},
        "fields": dict(payload.get("fields") or {}),
        "timestamp": normalize_timestamp(payload.get("timestamp")),
    }
