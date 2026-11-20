"""Behavioral checks for read-only scope discovery."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("discover", Path(__file__).parents[1] / "scripts" / "discover.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiscoverTests(unittest.TestCase):
    def test_scope_and_no_implicit_approval(self):
        for roots, expected in [((), "unconfigured"), (("fabric",), "fabric-only"), (("pbi",), "power-bi-only"), (("fabric", "pbi"), "mixed")]:
            with self.subTest(roots=roots), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for name in roots:
                    (root / name).mkdir()
                before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
                result = module.discover(root)
                after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
                self.assertEqual(result["scope_candidates"], expected)
                self.assertFalse(result["scope_approved"])
                self.assertEqual(result["fabric_git_connection"]["status"], "unknown")
                self.assertEqual(before, after)

    def test_existing_assets_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "cicd").mkdir()
            (root / "cicd" / "existing.yml").write_text("example", encoding="utf-8")
            self.assertEqual(module.discover(root)["existing_cicd_files"], ["cicd/existing.yml"])


if __name__ == "__main__":
    unittest.main()
