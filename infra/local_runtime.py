import fcntl
import json
import logging
import os
import signal
import subprocess
import sys
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from dotenv import load_dotenv

from Services.agent_service import AgentSettings

logger = logging.getLogger(__name__)

DOCKER_HEALTH_TIMEOUT_SECONDS = 120.0
API_HEALTH_TIMEOUT_SECONDS = 30.0
PROCESS_STOP_TIMEOUT_SECONDS = 10.0


class LocalRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ManagedProcess:
    name: str
    command: tuple[str, ...]
    marker: str
    pid_file: Path
    log_file: Path


class LocalRuntimeManager:
    def __init__(
        self,
        project_root: Path,
        python_executable: str | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.python_executable = python_executable or sys.executable
        self.runtime_dir = self.project_root / ".sentinela" / "runtime"
        self.logs_dir = self.project_root / ".sentinela" / "logs"
        self.lock_file = self.runtime_dir / "manager.lock"

    def start(self) -> None:
        with self._exclusive_lock():
            settings = self._validated_settings()
            api_port = self._local_api_port(settings.api_url)
            api = self._api_process(api_port)
            agent = self._agent_process()
            api_started = False
            agent_started = False

            try:
                self._run_compose("up", "-d")
                self._wait_for_url(
                    "http://127.0.0.1:8086/health",
                    "InfluxDB",
                    DOCKER_HEALTH_TIMEOUT_SECONDS,
                )
                self._wait_for_url(
                    "http://127.0.0.1:3000/api/health",
                    "Grafana",
                    DOCKER_HEALTH_TIMEOUT_SECONDS,
                )

                api_started = self._ensure_process(api)
                self._wait_for_url(
                    f"http://127.0.0.1:{api_port}/health",
                    "Sentinela API",
                    API_HEALTH_TIMEOUT_SECONDS,
                )
                agent_started = self._ensure_process(agent)
                time.sleep(0.5)
                if self._running_pid(agent) is None:
                    raise LocalRuntimeError(
                        f"Agent stopped during startup. Check {agent.log_file}."
                    )
            except Exception:
                if agent_started:
                    self._stop_process(agent)
                if api_started:
                    self._stop_process(api)
                raise

    def stop(self) -> None:
        with self._exclusive_lock():
            self._stop_process(self._agent_process())
            self._stop_process(self._api_process(self._configured_api_port()))
            self._run_compose("stop")

    def status(self) -> dict[str, bool]:
        api_port = self._configured_api_port()
        return {
            "influxdb": self._url_is_healthy("http://127.0.0.1:8086/health"),
            "grafana": self._url_is_healthy("http://127.0.0.1:3000/api/health"),
            "api": self._running_pid(self._api_process(api_port)) is not None
            and self._url_is_healthy(f"http://127.0.0.1:{api_port}/health"),
            "agent": self._running_pid(self._agent_process()) is not None,
        }

    def configured_api_url(self) -> str:
        api_port = self._configured_api_port()
        return f"http://127.0.0.1:{api_port}"

    def read_logs(self, service: str, lines: int) -> str:
        if lines <= 0:
            raise LocalRuntimeError("Log line count must be greater than zero.")

        processes = {
            "api": self._api_process(self._configured_api_port()),
            "agent": self._agent_process(),
        }
        if service not in processes:
            raise LocalRuntimeError(f"Unknown log service: {service}.")

        log_file = processes[service].log_file
        if not log_file.exists():
            return f"No log file exists for {service}."

        with log_file.open(encoding="utf-8", errors="replace") as stream:
            return "".join(deque(stream, maxlen=lines)).rstrip()

    def _validated_settings(self) -> AgentSettings:
        required_files = (
            self.project_root / ".env",
            self.project_root / "docker-compose.yml",
            self.project_root / "main.py",
            self.project_root / "agent.py",
        )
        missing = [path.name for path in required_files if not path.is_file()]
        if missing:
            raise LocalRuntimeError(
                f"Required local files are missing: {', '.join(missing)}."
            )

        load_dotenv(self.project_root / ".env", override=False)
        try:
            return AgentSettings.from_environment()
        except ValueError as exc:
            raise LocalRuntimeError(f"Invalid agent configuration: {exc}") from exc

    def _configured_api_port(self) -> int:
        load_dotenv(self.project_root / ".env", override=False)
        api_url = os.getenv("SENTINELA_API_URL", "http://127.0.0.1:8000")
        return self._local_api_port(api_url)

    @staticmethod
    def _local_api_port(api_url: str) -> int:
        parsed = urlparse(api_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.path not in {"", "/"}
        ):
            raise LocalRuntimeError(
                "Local runtime requires SENTINELA_API_URL to use localhost over HTTP."
            )
        return parsed.port or 8000

    def _api_process(self, port: int) -> ManagedProcess:
        return ManagedProcess(
            name="api",
            command=(
                self.python_executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ),
            marker="uvicorn main:app",
            pid_file=self.runtime_dir / "api.pid",
            log_file=self.logs_dir / "api.log",
        )

    def _agent_process(self) -> ManagedProcess:
        return ManagedProcess(
            name="agent",
            command=(
                self.python_executable,
                str(self.project_root / "agent.py"),
                "--log-level",
                "INFO",
            ),
            marker=str(self.project_root / "agent.py"),
            pid_file=self.runtime_dir / "agent.pid",
            log_file=self.logs_dir / "agent.log",
        )

    def _ensure_process(self, process: ManagedProcess) -> bool:
        if self._running_pid(process) is not None:
            logger.info("%s is already running.", process.name)
            return False

        unmanaged_pid = self._find_unmanaged_process(process.marker)
        if unmanaged_pid is not None:
            raise LocalRuntimeError(
                f"{process.name} is already running outside the manager with PID "
                f"{unmanaged_pid}. Stop it before continuing."
            )

        self._start_process(process)
        return True

    def _start_process(self, process: ManagedProcess) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        with process.log_file.open("ab", buffering=0) as log_stream:
            child = subprocess.Popen(
                process.command,
                cwd=self.project_root,
                stdin=subprocess.DEVNULL,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )

        process.pid_file.write_text(
            json.dumps({"pid": child.pid, "command": list(process.command)}),
            encoding="utf-8",
        )

    def _stop_process(self, process: ManagedProcess) -> None:
        pid = self._running_pid(process)
        if pid is None:
            process.pid_file.unlink(missing_ok=True)
            return

        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + PROCESS_STOP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self._process_command(pid) is None:
                break
            time.sleep(0.1)
        else:
            if self._process_matches(pid, process.marker):
                os.kill(pid, signal.SIGKILL)

        process.pid_file.unlink(missing_ok=True)

    def _running_pid(self, process: ManagedProcess) -> int | None:
        try:
            data = json.loads(process.pid_file.read_text(encoding="utf-8"))
            pid = int(data["pid"])
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

        if not self._process_matches(pid, process.marker):
            process.pid_file.unlink(missing_ok=True)
            return None
        return pid

    def _process_matches(self, pid: int, marker: str) -> bool:
        command = self._process_command(pid)
        return command is not None and marker in command

    @staticmethod
    def _process_command(pid: int) -> str | None:
        result = subprocess.run(
            ("ps", "-p", str(pid), "-o", "command="),
            text=True,
            capture_output=True,
            check=False,
        )
        command = result.stdout.strip()
        return command or None

    @staticmethod
    def _find_unmanaged_process(marker: str) -> int | None:
        result = subprocess.run(
            ("ps", "-axo", "pid=,command="),
            text=True,
            capture_output=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if not stripped or marker not in stripped:
                continue
            pid_text, _, _command = stripped.partition(" ")
            try:
                return int(pid_text)
            except ValueError:
                continue
        return None

    def _run_compose(self, *arguments: str) -> None:
        result = subprocess.run(
            ("docker", "compose", *arguments),
            cwd=self.project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip().splitlines()
            reason = detail[-1] if detail else "unknown Docker error"
            raise LocalRuntimeError(
                f"Docker Compose failed: {reason}. Start Docker Desktop and try again."
            )

    def _wait_for_url(self, url: str, name: str, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._url_is_healthy(url):
                return
            time.sleep(0.5)
        raise LocalRuntimeError(f"{name} did not become healthy within {timeout:.0f}s.")

    @staticmethod
    def _url_is_healthy(url: str) -> bool:
        try:
            with urlopen(url, timeout=2) as response:
                return 200 <= response.status < 300
        except (OSError, URLError):
            return False

    @contextmanager
    def _exclusive_lock(self) -> Iterator[None]:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_file.open("a+") as lock_stream:
            fcntl.flock(lock_stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_stream, fcntl.LOCK_UN)
