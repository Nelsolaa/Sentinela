import os
import unittest
from unittest.mock import patch

from Services.machine_context_service import get_machine_tags


class MachineContextServiceTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
