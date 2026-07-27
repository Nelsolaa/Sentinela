import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from infra.local_runtime import LocalRuntimeError, LocalRuntimeManager


class LocalRuntimeManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temporary_directory.name)
        self.manager = LocalRuntimeManager(
            self.project_root,
            python_executable="/test/python",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_start_obeys_dependency_order(self) -> None:
        events: list[str] = []
        settings = SimpleNamespace(api_url="http://127.0.0.1:8123")

        with (
            patch.object(self.manager, "_validated_settings", return_value=settings),
            patch.object(
                self.manager,
                "_run_compose",
                side_effect=lambda *_args: events.append("docker"),
            ),
            patch.object(
                self.manager,
                "_wait_for_url",
                side_effect=lambda _url, name, _timeout: events.append(name),
            ),
            patch.object(
                self.manager,
                "_ensure_process",
                side_effect=lambda process: events.append(process.name) or True,
            ),
            patch.object(self.manager, "_running_pid", return_value=123),
            patch("infra.local_runtime.time.sleep"),
        ):
            self.manager.start()

        self.assertEqual(
            events,
            ["docker", "InfluxDB", "Grafana", "api", "Sentinela API", "agent"],
        )

    def test_start_rolls_back_api_when_agent_fails(self) -> None:
        settings = SimpleNamespace(api_url="http://127.0.0.1:8000")
        stopped: list[str] = []

        def ensure_process(process):
            if process.name == "agent":
                raise LocalRuntimeError("agent failed")
            return True

        with (
            patch.object(self.manager, "_validated_settings", return_value=settings),
            patch.object(self.manager, "_run_compose"),
            patch.object(self.manager, "_wait_for_url"),
            patch.object(self.manager, "_ensure_process", side_effect=ensure_process),
            patch.object(
                self.manager,
                "_stop_process",
                side_effect=lambda process: stopped.append(process.name),
            ),
        ):
            with self.assertRaisesRegex(LocalRuntimeError, "agent failed"):
                self.manager.start()

        self.assertEqual(stopped, ["api"])

    def test_duplicate_unmanaged_process_is_rejected(self) -> None:
        process = self.manager._agent_process()

        with (
            patch.object(self.manager, "_running_pid", return_value=None),
            patch.object(self.manager, "_find_unmanaged_process", return_value=4321),
        ):
            with self.assertRaisesRegex(LocalRuntimeError, "PID 4321"):
                self.manager._ensure_process(process)

    def test_stop_obeys_reverse_dependency_order(self) -> None:
        events: list[str] = []

        with (
            patch.object(self.manager, "_configured_api_port", return_value=8000),
            patch.object(
                self.manager,
                "_stop_process",
                side_effect=lambda process: events.append(process.name),
            ),
            patch.object(
                self.manager,
                "_run_compose",
                side_effect=lambda *_args: events.append("docker"),
            ),
        ):
            self.manager.stop()

        self.assertEqual(events, ["agent", "api", "docker"])

    def test_read_logs_returns_only_requested_tail(self) -> None:
        self.manager.logs_dir.mkdir(parents=True)
        self.manager._agent_process().log_file.write_text(
            "first\nsecond\nthird\n",
            encoding="utf-8",
        )

        self.assertEqual(self.manager.read_logs("agent", 2), "second\nthird")

    def test_local_api_rejects_remote_or_non_http_urls(self) -> None:
        invalid_urls = (
            "https://127.0.0.1:8000",
            "http://192.168.1.10:8000",
            "http://localhost:8000/api",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(LocalRuntimeError):
                    self.manager._local_api_port(url)


if __name__ == "__main__":
    unittest.main()
