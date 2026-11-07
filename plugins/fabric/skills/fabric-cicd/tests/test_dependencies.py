import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("deps", Path(__file__).parents[1] / "scripts" / "validate_dependencies.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DependencyTests(unittest.TestCase):
    def test_valid_separate_domains(self):
        nodes = [{"name": "fabric-release", "domain": "fabric"}, {"name": "report", "domain": "power-bi", "depends_on": ["fabric-release"]}]
        self.assertEqual(module.validate_graph(nodes), [])

    def test_unknown_and_cycle_fail(self):
        self.assertTrue(module.validate_graph([{"name": "report", "domain": "power-bi", "depends_on": ["missing"]}]))
        self.assertTrue(module.validate_graph([{"name": "a", "domain": "power-bi", "depends_on": ["b"]}, {"name": "b", "domain": "power-bi", "depends_on": ["a"]}]))

    def test_credentials_are_rejected(self):
        self.assertTrue(module.validate_graph([{"name": "x", "domain": "fabric", "credentials": "not-allowed"}]))

if __name__ == "__main__":
    unittest.main()

class CrossDomainTests(unittest.TestCase):
    def test_mapping_prerequisite_must_be_fabric(self):
        import sys
        scripts = str(Path(__file__).parents[1] / "scripts")
        sys.path.insert(0, scripts)
        try:
            mapping = {"approved": True, "mappings": [{"name": "r", "source": "pbi/report.pbip", "workspace_id": "11111111-1111-4111-8111-111111111111", "fabric_prerequisites": ["f"]}]}
            self.assertEqual(module.validate_cross_domain(mapping, [{"name": "f", "domain": "fabric"}]), [])
            self.assertTrue(module.validate_cross_domain(mapping, [{"name": "f", "domain": "power-bi"}]))
        finally:
            sys.path.remove(scripts)
