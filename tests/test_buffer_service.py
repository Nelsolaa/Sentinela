import unittest
from unittest.mock import patch

from Services import buffer_service


class BufferServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        buffer_service._buffer.clear()

    def tearDown(self) -> None:
        buffer_service._buffer.clear()

    def test_hides_persistence_error_from_result(self) -> None:
        with (
            self.assertLogs("Services.buffer_service", level="ERROR"),
            patch(
                "Services.buffer_service.write_metric",
                side_effect=ConnectionError("secret database details"),
            ),
        ):
            result = buffer_service.send_with_buffer({"fields": {"cpu": 10}})

        self.assertFalse(result["persisted"])
        self.assertEqual(result["buffered"], 1)
        self.assertNotIn("error", result)

    def test_rejects_metric_when_buffer_is_full(self) -> None:
        buffer_service._buffer.append({"fields": {"cpu": 10}})

        with (
            patch.object(buffer_service, "MAX_BUFFER_ITEMS", 1),
            patch(
                "Services.buffer_service.write_metric",
                side_effect=ConnectionError("database unavailable"),
            ),
            self.assertLogs("Services.buffer_service", level="ERROR"),
        ):
            with self.assertRaises(buffer_service.BufferCapacityError):
                buffer_service.send_with_buffer({"fields": {"cpu": 20}})

        self.assertEqual(buffer_service.buffer_size(), 1)


if __name__ == "__main__":
    unittest.main()
