import unittest
from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import patch

from Services.system_metrics.cpu_service import get_cpu_metrics
from Services.system_metrics.disco_service import get_disk_metrics
from Services.system_metrics.gpu_service import get_gpu_metrics
from Services.system_metrics.memoria_service import get_memory_metrics
from Services.system_metrics.temperatura_service import get_temperature_metrics


class CpuServiceTests(unittest.TestCase):
    def test_formats_cpu_metrics(self) -> None:
        frequency = namedtuple("Frequency", "current min max")(2400, 1200, 3200)

        with (
            patch(
                "Services.system_metrics.cpu_service.cpu_collector.cpu_usage",
                return_value=18.5,
            ),
            patch(
                "Services.system_metrics.cpu_service.cpu_collector.cpu_nucleos",
                return_value=8,
            ),
            patch(
                "Services.system_metrics.cpu_service.cpu_collector.cpu_frequency",
                return_value=frequency,
            ),
        ):
            metrics = get_cpu_metrics()

        self.assertEqual(metrics["usage_percent"], 18.5)
        self.assertEqual(metrics["logical_cores"], 8)
        self.assertEqual(metrics["frequency_mhz"]["current"], 2400)


class MemoryServiceTests(unittest.TestCase):
    def test_formats_memory_metrics(self) -> None:
        raw_memory = SimpleNamespace(
            total=1000,
            available=600,
            used=400,
            free=200,
            percent=40.0,
        )

        with patch(
            "Services.system_metrics.memoria_service.memoria_collector.memory_usage",
            return_value=raw_memory,
        ):
            metrics = get_memory_metrics()

        self.assertEqual(
            metrics,
            {
                "total_bytes": 1000,
                "available_bytes": 600,
                "used_bytes": 400,
                "free_bytes": 200,
                "usage_percent": 40.0,
            },
        )


class DiskServiceTests(unittest.TestCase):
    def test_formats_disk_metrics(self) -> None:
        raw_disk = SimpleNamespace(total=2000, used=750, free=1250, percent=37.5)

        with patch(
            "Services.system_metrics.disco_service.disco_collector.disk_usage",
            return_value=raw_disk,
        ):
            metrics = get_disk_metrics()

        self.assertEqual(metrics["total_bytes"], 2000)
        self.assertEqual(metrics["used_bytes"], 750)
        self.assertEqual(metrics["free_bytes"], 1250)
        self.assertEqual(metrics["usage_percent"], 37.5)


class TemperatureServiceTests(unittest.TestCase):
    def test_formats_available_sensors(self) -> None:
        sensor = namedtuple("Sensor", "label current high critical")(
            "CPU", 48.0, 90.0, 100.0
        )

        with patch(
            "Services.system_metrics.temperatura_service.temperatura_collector.temperature",
            return_value={"coretemp": [sensor]},
        ):
            metrics = get_temperature_metrics()

        self.assertTrue(metrics["available"])
        self.assertEqual(metrics["sensors"]["coretemp"][0]["current"], 48.0)

    def test_handles_unavailable_sensors(self) -> None:
        with patch(
            "Services.system_metrics.temperatura_service.temperatura_collector.temperature",
            side_effect=RuntimeError("sensors unavailable"),
        ):
            metrics = get_temperature_metrics()

        self.assertFalse(metrics["available"])
        self.assertEqual(metrics["sensors"], {})
        self.assertEqual(metrics["error"], "sensors unavailable")


class GpuServiceTests(unittest.TestCase):
    def test_marks_gpu_metrics_as_mock(self) -> None:
        with (
            patch(
                "Services.system_metrics.gpu_service.gpu_collector.gpu_temp",
                return_value=45.0,
            ),
            patch(
                "Services.system_metrics.gpu_service.gpu_collector.gpu_usage",
                return_value=20.0,
            ),
            patch(
                "Services.system_metrics.gpu_service.gpu_collector.gpu_vram",
                return_value={"used_mb": 800, "total_mb": 4096},
            ),
        ):
            metrics = get_gpu_metrics()

        self.assertEqual(metrics["source"], "mock")
        self.assertEqual(metrics["temperature_celsius"], 45.0)
        self.assertEqual(metrics["usage_percent"], 20.0)
        self.assertEqual(metrics["vram"]["total_mb"], 4096)


if __name__ == "__main__":
    unittest.main()
