from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from Services.buffer_service import send_with_buffer
from Services.metrics_service import prepare_metric

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricPayload(BaseModel):
    measurement: str = Field(default="system_metrics", min_length=1)
    tags: dict[str, str] = Field(default_factory=dict)
    fields: dict[str, Any] = Field(default_factory=dict, min_length=1)
    timestamp: datetime | None = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def receive_metric(payload: MetricPayload) -> dict[str, Any]:
    metric = prepare_metric(payload.model_dump())
    result = send_with_buffer(metric)

    return {
        "accepted": True,
        "metric": metric,
        **result,
    }
