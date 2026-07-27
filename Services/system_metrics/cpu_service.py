from typing import Any

from Collectors import cpu_collector
from Services.system_metrics._converters import (
    as_dict,
    normalize_percentage,
    round_metric,
)


def get_cpu_metrics() -> dict[str, Any]:
    frequency = as_dict(cpu_collector.cpu_frequency())

    return {
        "usage_percent": normalize_percentage(cpu_collector.cpu_usage()),
        "logical_cores": cpu_collector.cpu_nucleos(),
        "frequency_mhz": {
            name: round_metric(value)
            for name, value in frequency.items()
            if value is not None
        },
    }
