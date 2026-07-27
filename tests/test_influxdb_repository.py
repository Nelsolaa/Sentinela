import unittest
from unittest.mock import Mock, patch

from influxdb_client.client.write_api import SYNCHRONOUS

from infra import influxdb_repository


class InfluxDBRepositoryTests(unittest.TestCase):
    def tearDown(self) -> None:
        influxdb_repository._client = None
        influxdb_repository._write_api = None

    def test_configures_synchronous_writes(self) -> None:
        client = Mock()
        write_api = Mock()
        client.write_api.return_value = write_api
        influxdb_repository._client = client

        configured = influxdb_repository._get_write_api()

        self.assertIs(configured, write_api)
        client.write_api.assert_called_once_with(write_options=SYNCHRONOUS)

    def test_reports_success_only_after_write_returns(self) -> None:
        client = Mock()
        client.ping.return_value = True
        write_api = Mock()

        with (
            patch.object(influxdb_repository, "_get_client", return_value=client),
            patch.object(
                influxdb_repository,
                "_get_write_api",
                return_value=write_api,
            ),
        ):
            influxdb_repository.write_metric(
                {
                    "measurement": "system_metrics",
                    "tags": {"host_id": "host-01"},
                    "fields": {"cpu_usage_percent": 10.0},
                }
            )

        write_api.write.assert_called_once()

    def test_closes_write_api_before_client(self) -> None:
        write_api = Mock()
        client = Mock()
        influxdb_repository._write_api = write_api
        influxdb_repository._client = client

        influxdb_repository.close()

        write_api.close.assert_called_once_with()
        client.close.assert_called_once_with()
        self.assertIsNone(influxdb_repository._write_api)
        self.assertIsNone(influxdb_repository._client)


if __name__ == "__main__":
    unittest.main()
