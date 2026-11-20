from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


class SkillSurfaceTests(unittest.TestCase):
    def test_ordered_workflow_uses_resolving_commands_and_stops_on_failure(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        commands = re.findall(r'<skill-path>/(scripts/(?:plan|approve|apply)\.py)', text)
        self.assertEqual(["scripts/plan.py", "scripts/approve.py", "scripts/apply.py"], commands)
        for relative in commands:
            self.assertTrue((SKILL / relative).is_file(), relative)
        for marker in ("1. Run read-only planning", "2. Review", "3. After explicit human review", "4. Apply", "5. Run the synthetic", "6. Commit"):
            self.assertIn(marker, text)
        self.assertIn("If any command exits nonzero", text)
        self.assertIn("stop", text)
        self.assertNotIn("Initialize-PowerBiCicd.ps1", text)
        self.assertNotIn("-Mode Plan", text)
        self.assertNotIn("-Mode Render", text)
        self.assertFalse((SKILL / "assets/templates/Initialize-PowerBiCicd.ps1").exists())
        self.assertFalse((SKILL / "assets/templates/bootstrap-config.json").exists())
        self.assertFalse((SKILL / "assets/templates/powerbi-assets.yml").exists())
        self.assertIn("<skill-path>/scripts/plan.py", text)
        self.assertIn("<skill-path>/scripts/approve.py", text)
        self.assertIn("<skill-path>/scripts/apply.py", text)
        self.assertIn("assets/migration-guide.md", text)
        guide = (SKILL / "assets/migration-guide.md").read_text(encoding="utf-8")
        for relative in (
            "cicd/powerbi/setup.yml", "cicd/powerbi/SETUP.md", "cicd/powerbi/setup.approved",
            "cicd/powerbi/bootstrap-config.json", "cicd/powerbi/powerbi-assets.yml",
            "cicd/powerbi/bindings.yml", "cicd/powerbi/azure-pipelines.yml",
            "cicd/powerbi/powerbi-validation.yml", "cicd/powerbi/scripts/",
            "cicd/powerbi/deployment/", "cicd/powerbi/apply-readiness.json",
        ):
            self.assertIn(relative, guide)


if __name__ == "__main__":
    unittest.main()
