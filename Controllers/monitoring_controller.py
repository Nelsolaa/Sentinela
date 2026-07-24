import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security, status

from Schemas.metric_schema import (
    HealthResponse,
    MetricIngestionResponse,
    MetricPayload,
)
from Security.api_keys import verify_ingest_api_key, verify_read_api_key
from Security.rate_limit import (
    health_rate_limit,
    ingest_rate_limit,
    read_rate_limit,
)
from Security.request_policy import require_json_content_type
from Services.buffer_service import BufferCapacityError, send_with_buffer
from Services.metrics_service import prepare_metric
from Services.server_metrics_service import get_server_metrics
from Services.system_metrics.cpu_service import get_cpu_metrics
from Services.system_metrics.disco_service import get_disk_metrics
from Services.system_metrics.gpu_service import get_gpu_metrics
from Services.system_metrics.memoria_service import get_memory_metrics
from Services.system_metrics.temperatura_service import get_temperature_metrics

logger = logging.getLogger(__name__)
router = APIRouter()

read_dependencies = [
    Depends(read_rate_limit),
    Security(verify_read_api_key),
]


@router.get(
    "/health",
    tags=["system"],
    response_model=HealthResponse,
    dependencies=[Depends(health_rate_limit)],
)
def health_check() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/metrics",
    tags=["metrics"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MetricIngestionResponse,
    dependencies=[
        Depends(ingest_rate_limit),
        Security(verify_ingest_api_key),
        Depends(require_json_content_type),
    ],
)
def receive_metric(payload: MetricPayload) -> MetricIngestionResponse:
    metric = prepare_metric(payload.model_dump())

    try:
        result = send_with_buffer(metric)
    except BufferCapacityError:
        logger.error("Metric rejected because the local buffer is full.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metric ingestion is temporarily unavailable.",
        ) from None

    return MetricIngestionResponse(
        metric=metric,
        persisted=result["persisted"],
        buffered=result["buffered"],
    )


@router.get(
    "/cpu",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_cpu_metrics() -> dict[str, Any]:
    return get_cpu_metrics()


@router.get(
    "/memoria",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_memory_metrics() -> dict[str, Any]:
    return get_memory_metrics()


@router.get(
    "/disco",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_disk_metrics() -> dict[str, Any]:
    return get_disk_metrics()


@router.get(
    "/temperatura",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_temperature_metrics() -> dict[str, Any]:
    return get_temperature_metrics()


@router.get(
    "/gpu",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_gpu_metrics() -> dict[str, Any]:
    return get_gpu_metrics()


@router.get(
    "/servidor",
    tags=["server metrics"],
    dependencies=read_dependencies,
)
def read_server_metrics() -> dict[str, Any]:
    try:
        return get_server_metrics()
    except ValueError:
        logger.exception("Invalid monitoring configuration.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring is temporarily unavailable.",
        ) from None
