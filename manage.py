import argparse
import logging
from pathlib import Path
from typing import Sequence

from infra.local_runtime import LocalRuntimeError, LocalRuntimeManager

PROJECT_ROOT = Path(__file__).resolve().parent


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage the local Sentinela monitoring pipeline."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="start Docker, API and agent")
    subparsers.add_parser("status", help="show component health")
    subparsers.add_parser("stop", help="stop agent, API and Docker services")

    logs_parser = subparsers.add_parser("logs", help="show local process logs")
    logs_parser.add_argument(
        "--service",
        choices=("api", "agent", "all"),
        default="all",
    )
    logs_parser.add_argument("--lines", type=int, default=100)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    manager = LocalRuntimeManager(PROJECT_ROOT)

    try:
        if arguments.command == "start":
            manager.start()
            print("Sentinela started.")
            print("Grafana: http://127.0.0.1:3000")
            print(f"API: {manager.configured_api_url()}")
            return 0

        if arguments.command == "stop":
            manager.stop()
            print("Sentinela stopped. Docker volumes were preserved.")
            return 0

        if arguments.command == "status":
            statuses = manager.status()
            for component, healthy in statuses.items():
                print(f"{component}: {'running' if healthy else 'stopped'}")
            return 0 if all(statuses.values()) else 1

        services = ("api", "agent") if arguments.service == "all" else (arguments.service,)
        for index, service in enumerate(services):
            if index:
                print()
            print(f"--- {service} ---")
            print(manager.read_logs(service, arguments.lines))
        return 0
    except LocalRuntimeError as exc:
        logging.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
