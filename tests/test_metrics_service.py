import unittest

from Services.metrics_service import prepare_metric


class MetricsServiceTests(unittest.TestCase):
    def test_preserves_canonical_fields_without_converting_again(self) -> None:
        fields = {
            "cpu_usage_percent": 1.0,
            "memory_used_gib": 10.25,
            "disk_free_gib": 320.5,
        }

        metric = prepare_metric(
            {
                "measurement": "system_metrics",
                "tags": {"host_id": "host-01"},
                "fields": fields,
            }
        )

        self.assertEqual(metric["fields"], fields)
        self.assertNotIn("memory_used_gib_gb", metric["fields"])


if __name__ == "__main__":
    unittest.main()
