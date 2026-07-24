from typing import Any


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if hasattr(value, "_asdict"):
        return dict(value._asdict())

    if isinstance(value, dict):
        return value

    return {"value": value}
