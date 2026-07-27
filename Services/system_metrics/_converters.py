from typing import Any

BYTES_PER_GIBIBYTE = 1024**3


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if hasattr(value, "_asdict"):
        return dict(value._asdict())

    if isinstance(value, dict):
        return value

    return {"value": value}


def bytes_to_gibibytes(value: Any) -> float:
    return round(float(value) / BYTES_PER_GIBIBYTE, 2)


def normalize_percentage(value: Any) -> float:
    percentage = float(value)
    return round(max(0.0, min(percentage, 100.0)), 2)


def round_metric(value: Any) -> float:
    return round(float(value), 2)
