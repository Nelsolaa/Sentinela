import os
import unittest
from unittest.mock import patch

import main
from Services.server_metrics_service import get_machine_tags, get_server_metrics


class MachineTagsTests(unittest.TestCase):
    def test_returns_normalized_machine_tags(self) -> None:
        environment = {
            "SENTINELA_HOST_ID": "vm-banco-01",
            "SENTINELA_MACHINE_TYPE": " VM ",
            "SENTINELA_ENV": "production",
        }

        with patch.dict(os.environ, environment):
            self.assertEqual(
                get_machine_tags(),
                {
                    "host_id": "vm-banco-01",
                    "machine_type": "vm",
                    "environment": "production",
                },
            )

    def test_rejects_invalid_machine_type(self) -> None:
        with patch.dict(os.environ, {"SENTINELA_MACHINE_TYPE": "container"}):
            with self.assertRaisesRegex(ValueError, "host, vm"):
                get_machine_tags()

    def test_server_snapshot_includes_machine_tags(self) -> None:
        with (
            patch.dict(os.environ, {"SENTINELA_MACHINE_TYPE": "host"}),
            patch(
                "Services.server_metrics_service.get_cpu_metrics",
                return_value={"usage_percent": 10.0},
            ),
            patch(
                "Services.server_metrics_service.get_memory_metrics",
                return_value={"usage_percent": 20.0},
            ),
            patch(
                "Services.server_metrics_service.get_disk_metrics",
                return_value={"usage_percent": 30.0},
            ),
            patch(
                "Services.server_metrics_service.get_temperature_metrics",
                return_value={"available": False},
            ),
            patch(
                "Services.server_metrics_service.get_gpu_metrics",
                return_value={"source": "mock"},
            ),
        ):
            snapshot = get_server_metrics()

        self.assertEqual(snapshot["tags"]["machine_type"], "host")
        self.assertEqual(snapshot["gpu"]["source"], "mock")


class ServerMetricsRoutesTests(unittest.TestCase):
    def test_routes_are_registered_in_openapi_schema(self) -> None:
        paths = set(main.app.openapi()["paths"])

        self.assertTrue(
            {"/cpu", "/memoria", "/disco", "/temperatura", "/gpu", "/servidor"}
            <= paths
        )


if __name__ == "__main__":
    unittest.main()
