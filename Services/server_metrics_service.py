import os
from typing import Any

from Collectors import (
    cpu_collector,
    disco_collector,
    gpu_collector,
    memoria_collector,
    temperatura_collector,
)

VALID_MACHINE_TYPES = frozenset({"host", "vm"})


def get_machine_tags() -> dict[str, str]:
    machine_type = os.getenv("SENTINELA_MACHINE_TYPE", "host").strip().lower()

    if machine_type not in VALID_MACHINE_TYPES:
        allowed = ", ".join(sorted(VALID_MACHINE_TYPES))
        raise ValueError(
            f"SENTINELA_MACHINE_TYPE must be one of: {allowed}."
        )

    return {
        "host_id": os.getenv("SENTINELA_HOST_ID", "local-host"),
        "machine_type": machine_type,
        "environment": os.getenv("SENTINELA_ENV", "development"),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}

    if hasattr(value, "_asdict"):
        return dict(value._asdict())

    if isinstance(value, dict):
        return value

    return {"value": value}


def get_cpu_metrics() -> dict[str, Any]:
    frequency = _as_dict(cpu_collector.cpu_frequency())

    return {
        "usage_percent": cpu_collector.cpu_usage(),
        "logical_cores": cpu_collector.cpu_nucleos(),
        "frequency_mhz": frequency,
    }


def get_memory_metrics() -> dict[str, Any]:
    memory = memoria_collector.memory_usage()

    return {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "free_bytes": memory.free,
        "usage_percent": memory.percent,
    }


def get_disk_metrics() -> dict[str, Any]:
    disk = disco_collector.disk_usage()

    return {
        "total_bytes": disk.total,
        "used_bytes": disk.used,
        "free_bytes": disk.free,
        "usage_percent": disk.percent,
    }


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
            name: [_as_dict(sensor) for sensor in entries]
            for name, entries in sensors.items()
        },
    }


def get_gpu_metrics() -> dict[str, Any]:
    return {
        "source": "mock",
        "temperature_celsius": gpu_collector.gpu_temp(),
        "usage_percent": gpu_collector.gpu_usage(),
        "vram": gpu_collector.gpu_vram(),
    }


def get_server_metrics() -> dict[str, Any]:
    return {
        "tags": get_machine_tags(),
        "cpu": get_cpu_metrics(),
        "memoria": get_memory_metrics(),
        "disco": get_disk_metrics(),
        "temperatura": get_temperature_metrics(),
        "gpu": get_gpu_metrics(),
    }
