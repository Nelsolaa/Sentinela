import argparse
import logging
import signal
from threading import Event
from typing import Sequence

from Services.agent_service import (
    AgentConfigurationError,
    AgentSettings,
    SentinelaAgent,
)

logger = logging.getLogger(__name__)


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and deliver Sentinela system metrics."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="run one collection cycle and exit",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    logging.basicConfig(
        level=getattr(logging, arguments.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        settings = AgentSettings.from_environment()
    except AgentConfigurationError as exc:
        logger.error("Invalid agent configuration: %s", exc)
        return 2

    agent = SentinelaAgent(settings)
    stop_event = Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("Signal %d received; stopping the agent.", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        if arguments.once:
            result = agent.run_cycle()
            return 0 if result.collected and result.queued == 0 else 1

        agent.run(stop_event)
        return 0
    finally:
        agent.close()


if __name__ == "__main__":
    raise SystemExit(main())
