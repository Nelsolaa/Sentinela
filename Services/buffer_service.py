from typing import Any

from infra.influxdb_repository import write_metric

_buffer: list[dict[str, Any]] = []


def _flush_buffer() -> None:
    pending = list(_buffer)
    _buffer.clear()

    for metric in pending:
        try:
            write_metric(metric)
        except Exception:
            _buffer.append(metric)
            raise


def send_with_buffer(metric: dict[str, Any]) -> dict[str, Any]:
    try:
        if _buffer:
            _flush_buffer()

        write_metric(metric)
        return {"persisted": True, "buffered": len(_buffer)}
    except Exception as exc:
        _buffer.append(metric)
        return {
            "persisted": False,
            "buffered": len(_buffer),
            "error": str(exc),
        }


def buffer_size() -> int:
    return len(_buffer)
