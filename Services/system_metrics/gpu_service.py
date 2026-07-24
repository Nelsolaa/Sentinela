from typing import Any

from Collectors import gpu_collector


def get_gpu_metrics() -> dict[str, Any]:
    return {
        "source": "mock",
        "temperature_celsius": gpu_collector.gpu_temp(),
        "usage_percent": gpu_collector.gpu_usage(),
        "vram": gpu_collector.gpu_vram(),
    }
