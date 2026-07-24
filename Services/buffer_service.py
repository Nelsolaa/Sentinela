import logging
import os
from threading import RLock
from typing import Any

from infra.influxdb_repository import write_metric

logger = logging.getLogger(__name__)

MAX_BUFFER_ITEMS = int(os.getenv("SENTINELA_BUFFER_MAX_ITEMS", "1000"))
if MAX_BUFFER_ITEMS <= 0:
    raise ValueError("SENTINELA_BUFFER_MAX_ITEMS must be greater than zero.")

_buffer: list[dict[str, Any]] = []
_buffer_lock = RLock()


class BufferCapacityError(RuntimeError):
    pass


def _enqueue(metric: dict[str, Any]) -> None:
    if len(_buffer) >= MAX_BUFFER_ITEMS:
        raise BufferCapacityError("Metric buffer capacity reached.")
    _buffer.append(metric)


def _flush_buffer() -> None:
    pending = list(_buffer)
    _buffer.clear()

    for index, metric in enumerate(pending):
        try:
            write_metric(metric)
        except Exception:
            _buffer.extend(pending[index:])
            raise


def send_with_buffer(metric: dict[str, Any]) -> dict[str, Any]:
    with _buffer_lock:
        try:
            if _buffer:
                _flush_buffer()

            write_metric(metric)
            return {"persisted": True, "buffered": len(_buffer)}
        except BufferCapacityError:
            raise
        except Exception:
            logger.exception("Metric persistence failed; buffering locally.")
            _enqueue(metric)
            return {
                "persisted": False,
                "buffered": len(_buffer),
            }


def buffer_size() -> int:
    with _buffer_lock:
        return len(_buffer)
