from typing import Any

from Collectors import gpu_collector
from Services.system_metrics._converters import normalize_percentage, round_metric


def get_gpu_metrics() -> dict[str, Any]:
    vram = gpu_collector.gpu_vram()

    return {
        "source": "mock",
        "temperature_celsius": round_metric(gpu_collector.gpu_temp()),
        "usage_percent": normalize_percentage(gpu_collector.gpu_usage()),
        "vram": {
            "used_mib": int(vram["used_mb"]),
            "total_mib": int(vram["total_mb"]),
        },
    }
