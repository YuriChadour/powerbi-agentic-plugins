from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from source_discovery import discover_source


class SourceDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "pbi"
        model = self.source / "Sales.SemanticModel"
        report = self.source / "Sales.Report"
        model.mkdir(parents=True)
        report.mkdir(parents=True)
        (model / ".platform").write_text(json.dumps({"metadata": {"displayName": "Sales Model"}}), encoding="utf-8")
        (model / "model.tmdl").write_text("model Sales", encoding="utf-8")
        (report / ".platform").write_text(json.dumps({"metadata": {"displayName": "Sales Report"}}), encoding="utf-8")
        (report / "definition.pbir").write_text(json.dumps({"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}}), encoding="utf-8")
        (self.source / "Sales.rdl").write_text('<Report xmlns="urn:schemas-microsoft-com:reporting"><DataSources><DataSource><DataSourceReference>/Finance/Production SQL</DataSourceReference></DataSource></DataSources></Report>', encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_discovers_stable_items_dependencies_and_rdl_binding(self) -> None:
        first = discover_source(self.root, "pbi")
        second = discover_source(self.root, "pbi")
        self.assertEqual(first, second)
        self.assertEqual([], first["gaps"])
        ids = [item["id"] for item in first["managed_items"]]
        self.assertEqual({"SalesModel", "SalesReport", "Sales"}, set(ids))
        self.assertLess(ids.index("SalesModel"), ids.index("SalesReport"))
        report = next(item for item in first["managed_items"] if item["type"] == "Report")
        self.assertEqual(["SalesModel"], report["dependencies"])
        rdl = next(item for item in first["managed_items"] if item["type"] == "PaginatedReport")
        self.assertEqual({"kind": "data_source", "target": "/Finance/Production SQL"}, rdl["binding"])
        self.assertFalse(first["external_writes"])

    def test_ambiguous_report_and_project_boundaries_are_blocking(self) -> None:
        (self.source / "Sales.Report" / "definition.pbir").write_text("{}", encoding="utf-8")
        (self.source / "Sales.pbip").write_text("{}", encoding="utf-8")
        report = discover_source(self.root, "pbi")
        self.assertTrue(any("model reference" in gap["reason"] for gap in report["gaps"]))
        self.assertTrue(any("PBIP project" in gap["reason"] for gap in report["gaps"]))

    def test_duplicate_display_names_are_blocking(self) -> None:
        other = self.source / "Other.SemanticModel"
        other.mkdir()
        (other / ".platform").write_text(json.dumps({"metadata": {"displayName": "Sales Model"}}), encoding="utf-8")
        (other / "model.tmdl").write_text("model Other", encoding="utf-8")
        result = discover_source(self.root, "pbi")
        self.assertTrue(any("ambiguous" in gap["reason"] for gap in result["gaps"]))
        self.assertTrue(any("duplicated" in gap["reason"] for gap in result["gaps"]))


if __name__ == "__main__":
    unittest.main()
