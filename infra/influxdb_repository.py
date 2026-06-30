import os
from datetime import datetime, timezone
from numbers import Number
from typing import Any

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, WriteOptions

load_dotenv()

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sentinela")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "metrics")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")

_client: InfluxDBClient | None = None
_write_api: Any | None = None


def _get_client() -> InfluxDBClient:
    global _client

    if _client is None:
        _client = InfluxDBClient(
            url=INFLUXDB_URL,
            token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG,
        )

    return _client


def _get_write_api() -> Any:
    global _write_api

    if _write_api is None:
        _write_api = _get_client().write_api(
            write_options=WriteOptions(
                batch_size=500,
                flush_interval=10_000,
                jitter_interval=2_000,
                retry_interval=5_000,
            )
        )

    return _write_api


def _escape_key(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )


def _escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_field_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value}i"

    if isinstance(value, float):
        return str(value)

    if isinstance(value, Number):
        return str(value)

    return f'"{_escape_string(str(value))}"'


def _timestamp_to_ns(value: Any) -> int:
    if value is None:
        return int(datetime.now(timezone.utc).timestamp() * 1_000_000_000)

    if isinstance(value, datetime):
        timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return int(timestamp.timestamp() * 1_000_000_000)

    if isinstance(value, (int, float)):
        return int(value)

    timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return int(timestamp.timestamp() * 1_000_000_000)


def metric_to_line_protocol(metric: dict[str, Any]) -> str:
    measurement = _escape_key(str(metric.get("measurement", "system_metrics")))
    tags = metric.get("tags") or {}
    fields = metric.get("fields") or {}
    timestamp = _timestamp_to_ns(metric.get("timestamp"))

    if not fields:
        raise ValueError("Metric must include at least one field.")

    tag_set = ",".join(
        f"{_escape_key(str(key))}={_escape_key(str(value))}"
        for key, value in sorted(tags.items())
        if value is not None
    )
    field_set = ",".join(
        f"{_escape_key(str(key))}={_format_field_value(value)}"
        for key, value in sorted(fields.items())
        if value is not None
    )

    measurement_and_tags = f"{measurement},{tag_set}" if tag_set else measurement
    return f"{measurement_and_tags} {field_set} {timestamp}"


def write_metric(metric: dict[str, Any]) -> None:
    line_protocol = metric_to_line_protocol(metric)

    if not _get_client().ping():
        raise ConnectionError("InfluxDB is not reachable.")

    _get_write_api().write(
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG,
        record=line_protocol,
    )


def close() -> None:
    global _client, _write_api

    if _write_api is not None:
        _write_api.flush()
        _write_api = None

    if _client is not None:
        _client.close()
        _client = None
