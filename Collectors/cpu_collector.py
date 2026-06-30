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


def collect_cpu_metric(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "measurement": "cpu",
        "tags": {
            "host_id": config["host_id"],
            "environment": config["environment"],
        },
        "fields": {
            "usage_percent": psutil.cpu_percent(interval=1),
            "logical_cores": psutil.cpu_count(logical=True),
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
        metric = collect_cpu_metric(config)
        post_metric(config, metric)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
