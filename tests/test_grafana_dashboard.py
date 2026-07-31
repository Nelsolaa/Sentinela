import json
import unittest
from pathlib import Path


DASHBOARD_PATH = (
    Path(__file__).resolve().parents[1] / "dashboards" / "sentinela-mvp.json"
)
DATASOURCE_UID = "sentinela-influxdb"


class GrafanaDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
        cls.panels = [
            element["spec"]
            for element in cls.dashboard["spec"]["elements"].values()
            if element["kind"] == "Panel"
        ]

    @staticmethod
    def _panel_name(panel: dict) -> str:
        defaults = panel["vizConfig"]["spec"]["fieldConfig"]["defaults"]
        return panel["title"] or defaults.get("displayName", "")

    @staticmethod
    def _queries(panel: dict) -> list[dict]:
        return [
            query["spec"]["query"]
            for query in panel["data"]["spec"].get("queries", [])
        ]

    def test_uses_portable_grafana_v2_resource(self) -> None:
        self.assertEqual(
            self.dashboard["apiVersion"],
            "dashboard.grafana.app/v2",
        )
        self.assertEqual(self.dashboard["kind"], "Dashboard")
        self.assertEqual(
            self.dashboard["metadata"],
            {"name": "sentinela-mvp-overview"},
        )

    def test_contains_expected_mvp_panels(self) -> None:
        names = {self._panel_name(panel) for panel in self.panels}

        self.assertTrue(
            {
                "CPU atual",
                "Memoria atual",
                "Disco atual",
                "Ultima coleta",
                "CPU ao longo do tempo",
                "Memoria ao longo do tempo",
                "Disco ao longo do tempo",
                "Capacidade de memoria",
                "Capacidade de disco",
            }.issubset(names)
        )

    def test_panel_ids_and_layout_references_are_unique(self) -> None:
        panel_ids = [panel["id"] for panel in self.panels]
        layout_items = self.dashboard["spec"]["layout"]["spec"]["items"]
        references = [item["spec"]["element"]["name"] for item in layout_items]

        self.assertEqual(len(panel_ids), len(set(panel_ids)))
        self.assertEqual(len(references), len(set(references)))
        self.assertEqual(len(self.panels), len(references))

    def test_all_queries_use_canonical_contract_and_datasource(self) -> None:
        queries = [query for panel in self.panels for query in self._queries(panel)]

        self.assertGreater(len(queries), 0)
        for query in queries:
            flux = query["spec"]["query"]
            self.assertEqual(query["datasource"]["name"], DATASOURCE_UID)
            self.assertIn('r._measurement == "system_metrics"', flux)
            self.assertIn('r.host_id == "${host_id}"', flux)
            self.assertNotIn('r._measurement == "cpu"', flux)
            self.assertNotIn('r._field == "usage_user"', flux)

    def test_host_variable_uses_canonical_tag(self) -> None:
        variables = {
            variable["spec"]["name"]: variable["spec"]
            for variable in self.dashboard["spec"]["variables"]
        }
        host_variable = variables["host_id"]

        self.assertEqual(
            host_variable["query"]["datasource"]["name"],
            DATASOURCE_UID,
        )
        self.assertIn('tag: "host_id"', host_variable["definition"])


if __name__ == "__main__":
    unittest.main()
