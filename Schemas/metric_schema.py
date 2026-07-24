from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    field_validator,
)

from Security.config import ALLOWED_MEASUREMENTS, ALLOWED_TAG_KEYS

SafeName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$",
    ),
]
MeasurementName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z][A-Za-z0-9_.-]*$",
    ),
]
TagValue = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]
TextFieldValue = Annotated[str, StringConstraints(max_length=512)]
IntegerFieldValue = Annotated[
    int,
    Field(strict=True, ge=-(2**63), le=(2**63) - 1),
]
FiniteFloat = Annotated[float, Field(strict=True, allow_inf_nan=False)]
MetricFieldValue = StrictBool | IntegerFieldValue | FiniteFloat | TextFieldValue


class MetricPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    measurement: MeasurementName = "system_metrics"
    tags: dict[SafeName, TagValue] = Field(default_factory=dict, max_length=20)
    fields: dict[SafeName, MetricFieldValue] = Field(min_length=1, max_length=50)
    timestamp: AwareDatetime | None = None

    @field_validator("measurement")
    @classmethod
    def validate_allowed_measurement(cls, value: str) -> str:
        if value not in ALLOWED_MEASUREMENTS:
            raise ValueError("Measurement is not allowed.")
        return value

    @field_validator("tags")
    @classmethod
    def validate_allowed_tags(cls, value: dict[str, str]) -> dict[str, str]:
        if not set(value) <= ALLOWED_TAG_KEYS:
            raise ValueError("One or more tag keys are not allowed.")
        return value

    @field_validator("fields", mode="before")
    @classmethod
    def validate_raw_integer_range(cls, value: object) -> object:
        if isinstance(value, dict):
            for field_value in value.values():
                if type(field_value) is int and not (-(2**63) <= field_value < 2**63):
                    raise ValueError("Integer field is outside the 64-bit range.")
        return value

    @field_validator("fields")
    @classmethod
    def validate_normalized_field_types(
        cls,
        value: dict[str, MetricFieldValue],
    ) -> dict[str, MetricFieldValue]:
        for key, field_value in value.items():
            lowered_key = key.lower()
            needs_number = (
                lowered_key.endswith("_bytes")
                or lowered_key in {"total", "used", "free"}
                or "percent" in lowered_key
                or "porcent" in lowered_key
                or lowered_key.endswith("_pct")
            )
            if needs_number and (
                isinstance(field_value, bool)
                or not isinstance(field_value, (int, float))
            ):
                raise ValueError(f"Field {key} must contain a numeric value.")

        return value


class PreparedMetric(BaseModel):
    measurement: str
    tags: dict[str, str]
    fields: dict[str, MetricFieldValue]
    timestamp: datetime | str


class MetricIngestionResponse(BaseModel):
    accepted: Literal[True] = True
    metric: PreparedMetric
    persisted: bool
    buffered: int = Field(ge=0)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
