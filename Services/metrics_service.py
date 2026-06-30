from datetime import datetime, timezone
from typing import Any


def bytes_to_gigabytes(value: Any) -> float:
    return round(float(value) / (1024**3), 2)


def normalize_percentage(value: Any) -> float:
    number = float(value)
    if 0 <= number <= 1:
        number *= 100
    return round(max(0.0, min(number, 100.0)), 2)


def normalize_timestamp(value: Any | None = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, datetime):
        timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat()

    timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return timestamp.astimezone(timezone.utc).isoformat()


def normalize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key, value in fields.items():
        if value is None:
            continue

        lowered_key = key.lower()
        if lowered_key.endswith("_bytes") or lowered_key in {"total", "used", "free"}:
            normalized[f"{key}_gb"] = bytes_to_gigabytes(value)
        elif "percent" in lowered_key or "porcent" in lowered_key or lowered_key.endswith("_pct"):
            normalized[key] = normalize_percentage(value)
        else:
            normalized[key] = value

    return normalized


def prepare_metric(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "measurement": payload.get("measurement", "system_metrics"),
        "tags": payload.get("tags") or {},
        "fields": normalize_fields(payload.get("fields") or {}),
        "timestamp": normalize_timestamp(payload.get("timestamp")),
    }
