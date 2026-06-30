from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import psutil
import requests

CONFIG_PATH = Path(__file__).resolve().parents[1] / ".agents" / "config.json"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


def collect_memory_metric(config: dict[str, Any]) -> dict[str, Any]:
    memory = psutil.virtual_memory()

    return {
        "measurement": "memory",
        "tags": {
            "host_id": config["host_id"],
            "environment": config["environment"],
        },
        "fields": {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_bytes": memory.used,
            "usage_percent": memory.percent,
        },
    }


def post_metric(config: dict[str, Any], metric: dict[str, Any]) -> None:
    response = requests.post(
        f"{config['api_url'].rstrip('/')}/metrics",
        json=metric,
        timeout=10,
    )
    response.raise_for_status()


def run(interval_seconds: int = 10) -> None:
    config = load_config()

    while True:
        metric = collect_memory_metric(config)
        post_metric(config, metric)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
