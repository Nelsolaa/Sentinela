import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ["SENTINELA_ALLOWED_HOSTS"] = "127.0.0.1,localhost,testserver"
os.environ["SENTINELA_INGEST_RATE_LIMIT"] = "30/minute"
os.environ["SENTINELA_RATE_LIMIT_STORAGE_URI"] = "memory://"

from Controllers import monitoring_controller
from Security.rate_limit import reset_rate_limits
from Services.buffer_service import BufferCapacityError
from main import app

INGEST_KEY = "i" * 64
READ_KEY = "r" * 64


class MonitoringSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_rate_limits()
        self.environment = patch.dict(
            os.environ,
            {
                "SENTINELA_INGEST_API_KEY": INGEST_KEY,
                "SENTINELA_READ_API_KEY": READ_KEY,
            },
        )
        self.environment.start()
        self.send_patch = patch.object(
            monitoring_controller,
            "send_with_buffer",
            return_value={"persisted": True, "buffered": 0},
        )
        self.send_patch.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.send_patch.stop()
        self.environment.stop()

    @staticmethod
    def valid_payload() -> dict[str, object]:
        return {
            "measurement": "system_metrics",
            "tags": {
                "host_id": "host-01",
                "machine_type": "host",
                "environment": "development",
                "os": "linux",
            },
            "fields": {
                "cpu_usage_percent": 25.5,
                "cpu_logical_cores": 8,
                "memory_total_gib": 16.0,
                "memory_available_gib": 6.0,
                "memory_used_gib": 10.0,
                "memory_free_gib": 2.0,
                "memory_usage_percent": 62.5,
                "disk_total_gib": 512.0,
                "disk_used_gib": 192.0,
                "disk_free_gib": 320.0,
                "disk_usage_percent": 37.5,
            },
        }

    def test_health_is_public_and_has_security_headers(self) -> None:
        response = self.client.get(
            "/health",
            headers={"Origin": "https://attacker.example"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_rejects_untrusted_host(self) -> None:
        response = self.client.get(
            "/health",
            headers={"Host": "attacker.example"},
        )

        self.assertEqual(response.status_code, 400)

    def test_read_route_requires_read_key(self) -> None:
        response = self.client.get("/cpu")

        self.assertEqual(response.status_code, 401)

    def test_read_route_rejects_incorrect_read_key(self) -> None:
        response = self.client.get(
            "/cpu",
            headers={"X-Sentinela-Read-Key": "x" * 64},
        )

        self.assertEqual(response.status_code, 401)

    def test_read_route_accepts_valid_read_key(self) -> None:
        with patch.object(
            monitoring_controller,
            "get_cpu_metrics",
            return_value={"usage_percent": 10.0},
        ):
            response = self.client.get(
                "/cpu",
                headers={"X-Sentinela-Read-Key": READ_KEY},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["usage_percent"], 10.0)
        self.assertIn("x-ratelimit-remaining", response.headers)

    def test_ingestion_requires_ingest_key(self) -> None:
        response = self.client.post("/metrics", json=self.valid_payload())

        self.assertEqual(response.status_code, 401)

    def test_ingestion_fails_closed_when_key_is_not_configured(self) -> None:
        with (
            patch.dict(os.environ, {"SENTINELA_INGEST_API_KEY": ""}),
            self.assertLogs("Security.api_keys", level="ERROR"),
        ):
            response = self.client.post(
                "/metrics",
                json=self.valid_payload(),
                headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "API security is not configured.")

    def test_accepts_valid_metric_without_exposing_internal_errors(self) -> None:
        with patch.object(
            monitoring_controller,
            "send_with_buffer",
            return_value={"persisted": False, "buffered": 1},
        ):
            response = self.client.post(
                "/metrics",
                json=self.valid_payload(),
                headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
            )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.json()["accepted"])
        self.assertFalse(response.json()["persisted"])
        self.assertNotIn("error", response.json())
        self.assertEqual(
            response.json()["metric"]["fields"],
            self.valid_payload()["fields"],
        )

    def test_rejects_unsupported_content_type(self) -> None:
        response = self.client.post(
            "/metrics",
            content="{}",
            headers={
                "Content-Type": "text/plain",
                "X-Sentinela-Ingest-Key": INGEST_KEY,
            },
        )

        self.assertEqual(response.status_code, 415)

    def test_rejects_payload_larger_than_configured_limit(self) -> None:
        response = self.client.post(
            "/metrics",
            content="x" * 33_000,
            headers={
                "Content-Type": "application/json",
                "X-Sentinela-Ingest-Key": INGEST_KEY,
            },
        )

        self.assertEqual(response.status_code, 413)

    def test_rejects_nested_and_unknown_fields(self) -> None:
        payload = self.valid_payload()
        payload["fields"] = {"cpu": {"nested": "not allowed"}}
        payload["unexpected"] = "value"

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_measurement_outside_allowlist(self) -> None:
        payload = self.valid_payload()
        payload["measurement"] = "attacker_measurement"

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_tag_to_control_cardinality(self) -> None:
        payload = self.valid_payload()
        payload["tags"] = {"attacker_tag": "unique-value"}

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_missing_required_tag(self) -> None:
        payload = self.valid_payload()
        del payload["tags"]["os"]

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_field_outside_contract(self) -> None:
        payload = self.valid_payload()
        payload["fields"]["attacker_field"] = 10

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_missing_required_metric_field(self) -> None:
        payload = self.valid_payload()
        del payload["fields"]["disk_usage_percent"]

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_integer_outside_influxdb_range(self) -> None:
        payload = self.valid_payload()
        payload["fields"]["cpu_logical_cores"] = 2**63

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_text_in_numeric_normalized_field(self) -> None:
        payload = self.valid_payload()
        payload["fields"]["cpu_usage_percent"] = "not-a-number"

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_percentage_outside_contract_range(self) -> None:
        payload = self.valid_payload()
        payload["fields"]["cpu_usage_percent"] = 101.0

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_rejects_negative_capacity(self) -> None:
        payload = self.valid_payload()
        payload["fields"]["memory_total_gib"] = -1.0

        response = self.client.post(
            "/metrics",
            json=payload,
            headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
        )

        self.assertEqual(response.status_code, 422)

    def test_returns_503_when_buffer_is_full(self) -> None:
        with (
            patch.object(
                monitoring_controller,
                "send_with_buffer",
                side_effect=BufferCapacityError,
            ),
            self.assertLogs("Controllers.monitoring_controller", level="ERROR"),
        ):
            response = self.client.post(
                "/metrics",
                json=self.valid_payload(),
                headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "Metric ingestion is temporarily unavailable.",
        )

    def test_rate_limits_ingestion_before_persistence(self) -> None:
        with patch.object(
            monitoring_controller,
            "send_with_buffer",
            return_value={"persisted": True, "buffered": 0},
        ) as send_metric:
            responses = [
                self.client.post(
                    "/metrics",
                    json=self.valid_payload(),
                    headers={"X-Sentinela-Ingest-Key": INGEST_KEY},
                )
                for _ in range(31)
            ]

        self.assertTrue(all(response.status_code == 202 for response in responses[:30]))
        self.assertEqual(responses[30].status_code, 429)
        self.assertIn("retry-after", responses[30].headers)
        self.assertEqual(send_metric.call_count, 30)


if __name__ == "__main__":
    unittest.main()
