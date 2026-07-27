from typing import Any

from Collectors import memoria_collector
from Services.system_metrics._converters import (
    bytes_to_gibibytes,
    normalize_percentage,
)


def get_memory_metrics() -> dict[str, Any]:
    memory = memoria_collector.memory_usage()

    return {
        "total_gib": bytes_to_gibibytes(memory.total),
        "available_gib": bytes_to_gibibytes(memory.available),
        "used_gib": bytes_to_gibibytes(memory.used),
        "free_gib": bytes_to_gibibytes(memory.free),
        "usage_percent": normalize_percentage(memory.percent),
    }
