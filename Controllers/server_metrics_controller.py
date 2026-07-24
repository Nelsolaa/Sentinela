from typing import Any

from fastapi import APIRouter

from Services.server_metrics_service import get_server_metrics
from Services.system_metrics.cpu_service import get_cpu_metrics
from Services.system_metrics.disco_service import get_disk_metrics
from Services.system_metrics.gpu_service import get_gpu_metrics
from Services.system_metrics.memoria_service import get_memory_metrics
from Services.system_metrics.temperatura_service import get_temperature_metrics

router = APIRouter(tags=["server metrics"])


@router.get("/cpu")
def read_cpu_metrics() -> dict[str, Any]:
    return get_cpu_metrics()


@router.get("/memoria")
def read_memory_metrics() -> dict[str, Any]:
    return get_memory_metrics()


@router.get("/disco")
def read_disk_metrics() -> dict[str, Any]:
    return get_disk_metrics()


@router.get("/temperatura")
def read_temperature_metrics() -> dict[str, Any]:
    return get_temperature_metrics()


@router.get("/gpu")
def read_gpu_metrics() -> dict[str, Any]:
    return get_gpu_metrics()


@router.get("/servidor")
def read_server_metrics() -> dict[str, Any]:
    return get_server_metrics()
