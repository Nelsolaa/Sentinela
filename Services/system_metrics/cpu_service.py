from typing import Any

from Collectors import cpu_collector
from Services.system_metrics._converters import as_dict


def get_cpu_metrics() -> dict[str, Any]:
    return {
        "usage_percent": cpu_collector.cpu_usage(),
        "logical_cores": cpu_collector.cpu_nucleos(),
        "frequency_mhz": as_dict(cpu_collector.cpu_frequency()),
    }
