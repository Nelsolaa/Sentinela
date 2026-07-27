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
SYSTEM_METRIC_MEASUREMENT = "system_metrics"

SYSTEM_METRIC_NUMERIC_FIELDS = frozenset(
    {
        "cpu_usage_percent",
        "cpu_frequency_current_mhz",
        "cpu_frequency_min_mhz",
        "cpu_frequency_max_mhz",
        "memory_total_gib",
        "memory_available_gib",
        "memory_used_gib",
        "memory_free_gib",
        "memory_usage_percent",
        "disk_total_gib",
        "disk_used_gib",
        "disk_free_gib",
        "disk_usage_percent",
        "temperature_average_celsius",
        "temperature_min_celsius",
        "temperature_max_celsius",
        "gpu_temperature_celsius",
        "gpu_usage_percent",
    }
)
SYSTEM_METRIC_INTEGER_FIELDS = frozenset(
    {
        "cpu_logical_cores",
        "temperature_sensor_count",
        "gpu_vram_used_mib",
        "gpu_vram_total_mib",
    }
)
SYSTEM_METRIC_BOOLEAN_FIELDS = frozenset({"temperature_available"})
SYSTEM_METRIC_TEXT_FIELDS = frozenset({"gpu_source"})
SYSTEM_METRIC_PERCENT_FIELDS = frozenset(
    {
        "cpu_usage_percent",
        "memory_usage_percent",
        "disk_usage_percent",
        "gpu_usage_percent",
    }
)
SYSTEM_METRIC_NON_NEGATIVE_FIELDS = frozenset(
    {
        "cpu_frequency_current_mhz",
        "cpu_frequency_min_mhz",
        "cpu_frequency_max_mhz",
        "memory_total_gib",
        "memory_available_gib",
        "memory_used_gib",
        "memory_free_gib",
        "disk_total_gib",
        "disk_used_gib",
        "disk_free_gib",
        "cpu_logical_cores",
        "temperature_sensor_count",
        "gpu_vram_used_mib",
        "gpu_vram_total_mib",
    }
)
SYSTEM_METRIC_FIELD_KEYS = (
    SYSTEM_METRIC_NUMERIC_FIELDS
    | SYSTEM_METRIC_INTEGER_FIELDS
    | SYSTEM_METRIC_BOOLEAN_FIELDS
    | SYSTEM_METRIC_TEXT_FIELDS
)
REQUIRED_SYSTEM_METRIC_FIELD_KEYS = frozenset(
    {
        "cpu_usage_percent",
        "cpu_logical_cores",
        "memory_total_gib",
        "memory_available_gib",
        "memory_used_gib",
        "memory_free_gib",
        "memory_usage_percent",
        "disk_total_gib",
        "disk_used_gib",
        "disk_free_gib",
        "disk_usage_percent",
    }
)
SYSTEM_METRIC_TAG_KEYS = frozenset(
    {"host_id", "machine_type", "environment", "os"}
)


class MetricPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    measurement: MeasurementName = "system_metrics"
    tags: dict[SafeName, TagValue] = Field(default_factory=dict, max_length=20)
    fields: dict[SafeName, MetricFieldValue] = Field(min_length=1, max_length=50)
    timestamp: AwareDatetime | None = None

    @field_validator("measurement")
    @classmethod
    def validate_allowed_measurement(cls, value: str) -> str:
        if value != SYSTEM_METRIC_MEASUREMENT:
            raise ValueError("Measurement must match the system metric contract.")
        return value

    @field_validator("tags")
    @classmethod
    def validate_allowed_tags(cls, value: dict[str, str]) -> dict[str, str]:
        if set(value) != SYSTEM_METRIC_TAG_KEYS:
            raise ValueError("System metric tags must match the contract.")
        if value["machine_type"] not in {"host", "vm"}:
            raise ValueError("machine_type must be host or vm.")
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
        field_keys = set(value)
        if not field_keys <= SYSTEM_METRIC_FIELD_KEYS:
            raise ValueError("One or more metric fields are not part of the contract.")
        if not REQUIRED_SYSTEM_METRIC_FIELD_KEYS <= field_keys:
            raise ValueError("Required system metric fields are missing.")

        for key, field_value in value.items():
            if key in SYSTEM_METRIC_NUMERIC_FIELDS and (
                isinstance(field_value, bool)
                or not isinstance(field_value, (int, float))
            ):
                raise ValueError(f"Field {key} must contain a numeric value.")
            if key in SYSTEM_METRIC_INTEGER_FIELDS and type(field_value) is not int:
                raise ValueError(f"Field {key} must contain an integer value.")
            if key in SYSTEM_METRIC_BOOLEAN_FIELDS and type(field_value) is not bool:
                raise ValueError(f"Field {key} must contain a boolean value.")
            if key in SYSTEM_METRIC_TEXT_FIELDS and not isinstance(field_value, str):
                raise ValueError(f"Field {key} must contain a text value.")
            if key in SYSTEM_METRIC_PERCENT_FIELDS and not 0 <= field_value <= 100:
                raise ValueError(f"Field {key} must be between zero and 100.")
            if key in SYSTEM_METRIC_NON_NEGATIVE_FIELDS and field_value < 0:
                raise ValueError(f"Field {key} must not be negative.")

        if value["cpu_logical_cores"] <= 0:
            raise ValueError("cpu_logical_cores must be greater than zero.")

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
