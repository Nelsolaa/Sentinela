from typing import Any

from Collectors import temperatura_collector
from Services.system_metrics._converters import as_dict


def get_temperature_metrics() -> dict[str, Any]:
    try:
        sensors = temperatura_collector.temperature()
    except Exception as exc:
        return {
            "available": False,
            "sensors": {},
            "error": str(exc),
        }

    return {
        "available": bool(sensors),
        "sensors": {
            name: [as_dict(sensor) for sensor in entries]
            for name, entries in sensors.items()
        },
    }
