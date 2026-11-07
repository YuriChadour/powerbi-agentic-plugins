"""Contract checks for optional Power BI mappings."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("pbi", Path(__file__).parents[1] / "scripts" / "validate_pbi_mapping.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MappingTests(unittest.TestCase):
    def test_explicit_mapping(self):
        valid = {"approved": True, "mappings": [{"name": "report", "source": "pbi/report.pbip", "workspace_id": "11111111-1111-4111-8111-111111111111", "fabric_prerequisites": ["fabric-release"]}]}
        self.assertEqual(module.validate(valid), [])

    def test_folder_alone_and_missing_approval_fail(self):
        self.assertTrue(module.validate({}))
        self.assertTrue(module.validate({"approved": False, "mappings": []}))

    def test_invalid_paths_ids_and_extra_fields_fail(self):
        bad = {"approved": True, "mappings": [{"name": "x", "source": "../outside", "workspace_id": "not-a-uuid", "password": "ignored"}]}
        self.assertGreaterEqual(len(module.validate(bad)), 3)


if __name__ == "__main__":
    unittest.main()
