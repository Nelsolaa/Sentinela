import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from Schemas.metric_schema import SYSTEM_METRIC_FIELD_KEYS
from Services.agent_queue_service import AgentQueue
from Services.agent_service import (
    AgentCycleResult,
    AgentDeliveryError,
    AgentHttpClient,
    AgentSettings,
    SentinelaAgent,
    build_metric_payload,
    canonicalize_queued_payload,
)


def settings(**overrides):
    values = {
        "api_url": "http://127.0.0.1:8000",
        "api_key": "a" * 64,
        "interval_seconds": 60.0,
        "request_timeout_seconds": 5.0,
        "max_attempts": 3,
        "retry_base_seconds": 1.0,
        "queue_path": ":memory:",
        "queue_max_items": 100,
        "flush_batch_size": 20,
    }
    values.update(overrides)
    return AgentSettings(**values)


def snapshot():
    return {
        "tags": {
            "host_id": "host-01",
            "machine_type": "host",
            "environment": "test",
        },
        "cpu": {
            "usage_percent": 25.0,
            "logical_cores": 8,
            "frequency_mhz": {"current": 2400.0, "min": 1200.0, "max": 3200.0},
        },
        "memoria": {
            "total_gib": 16.0,
            "available_gib": 6.0,
            "used_gib": 10.0,
            "free_gib": 2.0,
            "usage_percent": 40.0,
        },
        "disco": {
            "total_gib": 512.0,
            "used_gib": 192.0,
            "free_gib": 320.0,
            "usage_percent": 37.5,
        },
        "temperatura": {
            "available": True,
            "sensors": {
                "cpu": [
                    {"current": 40.0},
                    {"current": 50.0},
                ]
            },
        },
        "gpu": {
            "source": "mock",
            "temperature_celsius": 45.0,
            "usage_percent": 20.0,
            "vram": {"used_mib": 800, "total_mib": 4096},
        },
    }


class AgentPayloadTests(unittest.TestCase):
    def test_builds_flat_metric_payload(self) -> None:
        with (
            patch(
                "Services.agent_service.get_server_metrics",
                return_value=snapshot(),
            ),
            patch("Services.agent_service.platform.system", return_value="Linux"),
        ):
            payload = build_metric_payload()

        self.assertEqual(payload["measurement"], "system_metrics")
        self.assertEqual(payload["tags"]["os"], "linux")
        self.assertEqual(payload["fields"]["cpu_usage_percent"], 25.0)
        self.assertEqual(payload["fields"]["memory_total_gib"], 16.0)
        self.assertEqual(payload["fields"]["disk_total_gib"], 512.0)
        self.assertEqual(payload["fields"]["temperature_average_celsius"], 45.0)
        self.assertEqual(payload["fields"]["gpu_source"], "mock")
        self.assertEqual(set(payload["fields"]), SYSTEM_METRIC_FIELD_KEYS)
        self.assertTrue(all(not isinstance(value, dict) for value in payload["fields"].values()))

    def test_converts_payload_from_legacy_persistent_queue(self) -> None:
        payload = {
            "fields": {
                "memory_total_bytes": 16 * (1024**3),
                "disk_free_bytes": 320 * (1024**3),
                "gpu_vram_used_mb": 800,
            }
        }

        canonical = canonicalize_queued_payload(payload)

        self.assertEqual(canonical["fields"]["memory_total_gib"], 16.0)
        self.assertEqual(canonical["fields"]["disk_free_gib"], 320.0)
        self.assertEqual(canonical["fields"]["gpu_vram_used_mib"], 800)
        self.assertIn("memory_total_bytes", payload["fields"])


class AgentQueueTests(unittest.TestCase):
    def test_persists_pending_metrics_between_instances(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "agent.sqlite3")
            queue = AgentQueue(path, max_items=10)
            queue.enqueue({"fields": {"cpu_usage_percent": 10.0}})
            queue.close()

            reopened = AgentQueue(path, max_items=10)
            try:
                self.assertEqual(reopened.size(), 1)
                self.assertEqual(
                    reopened.pending(1)[0][1]["fields"]["cpu_usage_percent"],
                    10.0,
                )
            finally:
                reopened.close()


class AgentHttpClientTests(unittest.TestCase):
    def test_retries_temporary_connection_error(self) -> None:
        response = Mock(status_code=202, headers={})
        response.json.return_value = {"accepted": True, "persisted": True, "buffered": 0}
        session = Mock()
        session.post.side_effect = [requests.ConnectionError("offline"), response]
        sleeper = Mock()
        client = AgentHttpClient(settings(), session=session, sleeper=sleeper)

        result = client.send({"fields": {"cpu_usage_percent": 10.0}})

        self.assertTrue(result["accepted"])
        self.assertEqual(session.post.call_count, 2)
        sleeper.assert_called_once_with(1.0)

    def test_does_not_retry_authentication_error(self) -> None:
        response = Mock(status_code=401, headers={})
        session = Mock()
        session.post.return_value = response
        client = AgentHttpClient(settings(), session=session, sleeper=Mock())

        with self.assertRaisesRegex(AgentDeliveryError, "HTTP 401"):
            client.send({"fields": {"cpu_usage_percent": 10.0}})

        self.assertEqual(session.post.call_count, 1)


class SentinelaAgentTests(unittest.TestCase):
    def test_keeps_metric_queued_until_api_recovers(self) -> None:
        queue = AgentQueue(":memory:", max_items=10)
        client = Mock()
        client.send.side_effect = [
            AgentDeliveryError("offline"),
            {"accepted": True},
            {"accepted": True},
        ]
        payload_builder = Mock(
            side_effect=[
                {"fields": {"cpu_usage_percent": 10.0}},
                {"fields": {"cpu_usage_percent": 20.0}},
            ]
        )
        agent = SentinelaAgent(
            settings(),
            client=client,
            queue=queue,
            payload_builder=payload_builder,
        )

        first = agent.run_cycle()
        second = agent.run_cycle()

        self.assertEqual(first, AgentCycleResult(True, 0, 1))
        self.assertEqual(second, AgentCycleResult(True, 2, 0))
        sent_values = [
            call.args[0]["fields"]["cpu_usage_percent"]
            for call in client.send.call_args_list
        ]
        self.assertEqual(sent_values, [10.0, 10.0, 20.0])
        queue.close()

    def test_flushes_full_queue_before_storing_current_metric(self) -> None:
        queue = AgentQueue(":memory:", max_items=1)
        queue.enqueue({"fields": {"cpu_usage_percent": 10.0}})
        client = Mock()
        client.send.return_value = {"accepted": True}
        agent = SentinelaAgent(
            settings(queue_max_items=1),
            client=client,
            queue=queue,
            payload_builder=lambda: {"fields": {"cpu_usage_percent": 20.0}},
        )

        result = agent.run_cycle()

        self.assertEqual(result, AgentCycleResult(True, 2, 0))
        sent_values = [
            call.args[0]["fields"]["cpu_usage_percent"]
            for call in client.send.call_args_list
        ]
        self.assertEqual(sent_values, [10.0, 20.0])
        queue.close()


if __name__ == "__main__":
    unittest.main()
