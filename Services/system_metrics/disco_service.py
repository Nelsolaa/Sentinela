from typing import Any

from Collectors import disco_collector


def get_disk_metrics() -> dict[str, Any]:
    disk = disco_collector.disk_usage()

    return {
        "total_bytes": disk.total,
        "used_bytes": disk.used,
        "free_bytes": disk.free,
        "usage_percent": disk.percent,
    }
