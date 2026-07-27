import logging
from typing import Any

from Collectors import temperatura_collector
from Services.system_metrics._converters import as_dict

logger = logging.getLogger(__name__)


def get_temperature_metrics() -> dict[str, Any]:
    try:
        sensors = temperatura_collector.temperature()
    except (AttributeError, NotImplementedError):
        logger.info("Temperature sensors are not supported on this platform.")
        return {
            "available": False,
            "sensors": {},
            "error": "temperature_sensors_unavailable",
        }
    except Exception:
        logger.exception("Temperature sensors are unavailable.")
        return {
            "available": False,
            "sensors": {},
            "error": "temperature_sensors_unavailable",
        }

    return {
        "available": bool(sensors),
        "sensors": {
            name: [as_dict(sensor) for sensor in entries]
            for name, entries in sensors.items()
        },
    }
