from typing import Any

from Collectors import memoria_collector


def get_memory_metrics() -> dict[str, Any]:
    memory = memoria_collector.memory_usage()

    return {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "free_bytes": memory.free,
        "usage_percent": memory.percent,
    }
