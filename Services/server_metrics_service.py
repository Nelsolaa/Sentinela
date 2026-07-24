from typing import Any

from Services.machine_context_service import get_machine_tags
from Services.system_metrics.cpu_service import get_cpu_metrics
from Services.system_metrics.disco_service import get_disk_metrics
from Services.system_metrics.gpu_service import get_gpu_metrics
from Services.system_metrics.memoria_service import get_memory_metrics
from Services.system_metrics.temperatura_service import get_temperature_metrics


def get_server_metrics() -> dict[str, Any]:
    return {
        "tags": get_machine_tags(),
        "cpu": get_cpu_metrics(),
        "memoria": get_memory_metrics(),
        "disco": get_disk_metrics(),
        "temperatura": get_temperature_metrics(),
        "gpu": get_gpu_metrics(),
    }
