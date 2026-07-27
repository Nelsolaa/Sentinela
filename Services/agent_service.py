import logging
import math
import os
import platform
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event
from typing import Any, Callable
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from Services.agent_queue_service import AgentQueue, AgentQueueCapacityError
from Services.server_metrics_service import get_server_metrics

load_dotenv()

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
PLACEHOLDER_KEY_PARTS = ("change-me", "replace")


class AgentConfigurationError(ValueError):
    pass


class AgentDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentSettings:
    api_url: str
    api_key: str
    interval_seconds: float
    request_timeout_seconds: float
    max_attempts: int
    retry_base_seconds: float
    queue_path: str
    queue_max_items: int
    flush_batch_size: int

    @classmethod
    def from_environment(cls) -> "AgentSettings":
        api_url = os.getenv("SENTINELA_API_URL", "http://127.0.0.1:8000").rstrip("/")
        parsed_url = urlparse(api_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise AgentConfigurationError("SENTINELA_API_URL must be a valid HTTP URL.")

        api_key = os.getenv("SENTINELA_INGEST_API_KEY", "").strip()
        lowered_key = api_key.lower()
        if len(api_key) < 32 or any(part in lowered_key for part in PLACEHOLDER_KEY_PARTS):
            raise AgentConfigurationError(
                "SENTINELA_INGEST_API_KEY must contain a secure configured key."
            )

        return cls(
            api_url=api_url,
            api_key=api_key,
            interval_seconds=_positive_float_setting(
                "SENTINELA_AGENT_INTERVAL_SECONDS", 60.0
            ),
            request_timeout_seconds=_positive_float_setting(
                "SENTINELA_AGENT_REQUEST_TIMEOUT_SECONDS", 10.0
            ),
            max_attempts=_positive_int_setting("SENTINELA_AGENT_MAX_ATTEMPTS", 3),
            retry_base_seconds=_positive_float_setting(
                "SENTINELA_AGENT_RETRY_BASE_SECONDS", 1.0
            ),
            queue_path=os.getenv(
                "SENTINELA_AGENT_QUEUE_PATH",
                ".sentinela/agent_queue.sqlite3",
            ),
            queue_max_items=_positive_int_setting(
                "SENTINELA_AGENT_QUEUE_MAX_ITEMS", 10_000
            ),
            flush_batch_size=_positive_int_setting(
                "SENTINELA_AGENT_FLUSH_BATCH_SIZE", 20
            ),
        )


@dataclass(frozen=True)
class AgentCycleResult:
    collected: bool
    delivered: int
    queued: int


def _positive_float_setting(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise AgentConfigurationError(f"{name} must be a number.") from exc

    if not math.isfinite(value) or value <= 0:
        raise AgentConfigurationError(f"{name} must be greater than zero.")
    return value


def _positive_int_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise AgentConfigurationError(f"{name} must be an integer.") from exc

    if value <= 0:
        raise AgentConfigurationError(f"{name} must be greater than zero.")
    return value


def _numeric_values(values: list[Any]) -> list[float]:
    return [
        float(value)
        for value in values
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    ]


def _temperature_fields(temperature: dict[str, Any]) -> dict[str, Any]:
    readings: list[Any] = []
    for sensors in temperature.get("sensors", {}).values():
        readings.extend(sensor.get("current") for sensor in sensors)

    current_values = _numeric_values(readings)
    fields: dict[str, Any] = {
        "temperature_available": bool(temperature.get("available")),
        "temperature_sensor_count": len(current_values),
    }
    if current_values:
        fields.update(
            {
                "temperature_average_celsius": round(
                    sum(current_values) / len(current_values), 2
                ),
                "temperature_min_celsius": min(current_values),
                "temperature_max_celsius": max(current_values),
            }
        )
    return fields


def build_metric_payload() -> dict[str, Any]:
    snapshot = get_server_metrics()
    cpu = snapshot["cpu"]
    memory = snapshot["memoria"]
    disk = snapshot["disco"]
    gpu = snapshot["gpu"]
    frequency = cpu.get("frequency_mhz", {})
    vram = gpu.get("vram", {})

    fields: dict[str, Any] = {
        "cpu_usage_percent": cpu["usage_percent"],
        "cpu_logical_cores": cpu["logical_cores"],
        "memory_total_bytes": memory["total_bytes"],
        "memory_available_bytes": memory["available_bytes"],
        "memory_used_bytes": memory["used_bytes"],
        "memory_free_bytes": memory["free_bytes"],
        "memory_usage_percent": memory["usage_percent"],
        "disk_total_bytes": disk["total_bytes"],
        "disk_used_bytes": disk["used_bytes"],
        "disk_free_bytes": disk["free_bytes"],
        "disk_usage_percent": disk["usage_percent"],
        "gpu_source": gpu["source"],
        "gpu_temperature_celsius": gpu["temperature_celsius"],
        "gpu_usage_percent": gpu["usage_percent"],
        "gpu_vram_used_mb": vram["used_mb"],
        "gpu_vram_total_mb": vram["total_mb"],
        **_temperature_fields(snapshot["temperatura"]),
    }

    for name in ("current", "min", "max"):
        value = frequency.get(name)
        if value is not None:
            fields[f"cpu_frequency_{name}_mhz"] = value

    return {
        "measurement": "system_metrics",
        "tags": {
            **snapshot["tags"],
            "os": platform.system().strip().lower() or "unknown",
        },
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class AgentHttpClient:
    def __init__(
        self,
        settings: AgentSettings,
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._session = session or requests.Session()
        self._sleeper = sleeper

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self._settings.api_url}/metrics"
        last_error = "unknown delivery failure"

        for attempt in range(1, self._settings.max_attempts + 1):
            response: requests.Response | None = None
            try:
                response = self._session.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "X-Sentinela-Ingest-Key": self._settings.api_key,
                    },
                    timeout=self._settings.request_timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = f"API connection failed: {type(exc).__name__}"
            else:
                if 200 <= response.status_code < 300:
                    try:
                        body = response.json()
                    except requests.exceptions.JSONDecodeError as exc:
                        raise AgentDeliveryError(
                            "API returned an invalid success response."
                        ) from exc
                    if body.get("accepted") is not True:
                        raise AgentDeliveryError("API did not confirm metric acceptance.")
                    return body

                last_error = f"API returned HTTP {response.status_code}"
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise AgentDeliveryError(last_error)

            if attempt < self._settings.max_attempts:
                self._sleeper(self._retry_delay(attempt, response))

        raise AgentDeliveryError(last_error)

    def _retry_delay(
        self,
        attempt: int,
        response: requests.Response | None,
    ) -> float:
        backoff = self._settings.retry_base_seconds * (2 ** (attempt - 1))
        if response is None:
            return backoff

        retry_after = response.headers.get("Retry-After", "")
        try:
            return max(backoff, float(retry_after))
        except ValueError:
            return backoff

    def close(self) -> None:
        self._session.close()


class SentinelaAgent:
    def __init__(
        self,
        settings: AgentSettings,
        client: AgentHttpClient | None = None,
        queue: AgentQueue | None = None,
        payload_builder: Callable[[], dict[str, Any]] = build_metric_payload,
    ) -> None:
        self._settings = settings
        self._client = client or AgentHttpClient(settings)
        self._queue = queue or AgentQueue(
            settings.queue_path,
            settings.queue_max_items,
        )
        self._payload_builder = payload_builder

    def run_cycle(self) -> AgentCycleResult:
        try:
            payload = self._payload_builder()
        except Exception:
            logger.exception("Metric collection failed.")
            return AgentCycleResult(False, 0, self._queue.size())

        delivered = 0
        try:
            self._queue.enqueue(payload)
        except AgentQueueCapacityError:
            logger.warning("Agent queue is full; attempting recovery before enqueue.")
            delivered = self._deliver_pending(self._settings.flush_batch_size)
            try:
                self._queue.enqueue(payload)
            except AgentQueueCapacityError:
                logger.error("Agent queue is full; the current metric was not stored.")
                return AgentCycleResult(False, delivered, self._queue.size())

        remaining_batch = self._settings.flush_batch_size - delivered
        if remaining_batch > 0:
            delivered += self._deliver_pending(remaining_batch)

        queued = self._queue.size()
        logger.info(
            "Agent cycle completed: delivered=%d queued=%d",
            delivered,
            queued,
        )
        return AgentCycleResult(True, delivered, queued)

    def _deliver_pending(self, limit: int) -> int:
        delivered = 0
        for item_id, pending_payload in self._queue.pending(limit):
            try:
                self._client.send(pending_payload)
            except AgentDeliveryError as exc:
                logger.warning("Metric delivery postponed: %s", exc)
                break
            self._queue.acknowledge(item_id)
            delivered += 1
        return delivered

    def run(self, stop_event: Event) -> None:
        logger.info(
            "Sentinela agent started with interval %.2fs.",
            self._settings.interval_seconds,
        )
        while not stop_event.is_set():
            started_at = time.monotonic()
            self.run_cycle()
            elapsed = time.monotonic() - started_at
            stop_event.wait(max(0.0, self._settings.interval_seconds - elapsed))

    def close(self) -> None:
        self._client.close()
        self._queue.close()
