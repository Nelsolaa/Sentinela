from typing import Any

from Collectors import disco_collector
from Services.system_metrics._converters import (
    bytes_to_gibibytes,
    normalize_percentage,
)


def get_disk_metrics() -> dict[str, Any]:
    disk = disco_collector.disk_usage()

    return {
        "total_gib": bytes_to_gibibytes(disk.total),
        "used_gib": bytes_to_gibibytes(disk.used),
        "free_gib": bytes_to_gibibytes(disk.free),
        "usage_percent": normalize_percentage(disk.percent),
    }
