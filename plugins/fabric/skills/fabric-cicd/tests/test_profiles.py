"""Offline profile-model regression tests."""
from __future__ import annotations

import sys
import unittest
import copy
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "tests"))
from profiles import ProfileError, normalize_setup, route_branch, translate_v1  # noqa: E402
from test_apply import make_setup  # noqa: E402

import importlib.util

_loader_spec = importlib.util.spec_from_file_location("runtime_profile_loader", SKILL / "assets" / "cicd" / "fabric" / "profile_loader.py")
runtime_profiles = importlib.util.module_from_spec(_loader_spec)
_loader_spec.loader.exec_module(runtime_profiles)


class ProfileTests(unittest.TestCase):
    def profile_setup(self):
        return translate_v1(make_setup())

    def test_v1_translation_is_deterministic_and_preserves_four_profiles(self):
        first, second = normalize_setup(make_setup()), normalize_setup(make_setup())
        self.assertEqual(first, second)
        self.assertEqual(["TEST", "HOTFIX"], first["profiles"]["PROD"]["promotion"]["accepts_from"])
        self.assertEqual("BAM-IaC-CloudEng", first["profiles"]["DEV"]["azure_devops"]["private_pool"])
        legacy = make_setup()["environments"]
        for key, profile in first["profiles"].items():
            with self.subTest(key=key):
                self.assertEqual(legacy[key]["branch"], profile["source_branch"])
                self.assertEqual(legacy[key]["workspace"], profile["workspace"])
                self.assertEqual(legacy[key]["pipeline_name"], profile["azure_devops"]["pipeline_name"])
                self.assertEqual(legacy[key]["pipeline_yaml"], profile["azure_devops"]["pipeline_yaml"])
                self.assertEqual(legacy[key]["ado_environment"], profile["azure_devops"]["protected_environment"])
                self.assertEqual(legacy[key]["private_pool"]["name"], profile["azure_devops"]["private_pool"])
                self.assertEqual(legacy[key]["key_vault"], profile["credentials"]["key_vault"])

    def test_additional_profile_needs_no_source_change(self):
        setup = self.profile_setup()
        profile = setup["profiles"]["TEST"].copy()
        profile["workspace"] = {"name": "WS TEST2", "id": "55555555-1111-4111-8111-111111111111", "create": False, "capacity": {"id": "cap", "name": "Cap"}}
        profile["source_branch"] = "test2"
        profile["azure_devops"] = dict(profile["azure_devops"], pipeline_name="Repo Fabric TEST2", pipeline_yaml="cicd/fabric/fabric-test2.yml", protected_environment="fabric-test2")
        setup["profiles"]["TEST2"] = profile
        self.assertIn("TEST2", normalize_setup(setup)["profiles"])

    def test_conflicts_and_metacharacters_fail_with_profile_context(self):
        setup = self.profile_setup()
        setup["profiles"]["TEST"]["source_branch"] = "DEV"
        with self.assertRaisesRegex(ProfileError, "profile TEST.*source_branch"):
            normalize_setup(setup)
        setup = self.profile_setup()
        setup["profiles"]["TEST"]["azure_devops"]["pipeline_name"] = "bad; command"
        with self.assertRaisesRegex(ProfileError, "profile TEST.*pipeline_name"):
            normalize_setup(setup)

    def test_each_required_profile_field_fails_with_profile_context(self):
        paths = (
            ("source_branch",), ("workspace", "name"), ("workspace", "capacity", "name"),
            ("azure_devops", "pipeline_name"), ("azure_devops", "pipeline_yaml"),
            ("azure_devops", "protected_environment"), ("azure_devops", "variable_group"),
            ("azure_devops", "private_pool"), ("credentials", "key_vault", "service_connection"),
            ("credentials", "key_vault", "name"), ("credentials", "key_vault", "secret"),
        )
        for path in paths:
            with self.subTest(path=path):
                setup = self.profile_setup()
                value = setup["profiles"]["TEST"]
                for part in path[:-1]: value = value[part]
                value[path[-1]] = ""
                with self.assertRaisesRegex(ProfileError, "profile TEST"):
                    normalize_setup(setup)

    def test_boolean_and_promotion_contracts_are_fail_closed(self):
        for path, value in (
            (("deploy", "enabled"), "yes"),
            (("verification", "manual_boundary"), "no"),
            (("promotion", "accepts_from"), ["UNKNOWN"]),
            (("promotion", "accepts_from"), ["DEV", "DEV"]),
        ):
            with self.subTest(path=path, value=value):
                setup = self.profile_setup()
                node = setup["profiles"]["TEST"]
                for part in path[:-1]: node = node[part]
                node[path[-1]] = value
                with self.assertRaisesRegex(ProfileError, "profile TEST"):
                    normalize_setup(setup)

    def test_conflicting_profile_identities_fail_before_apply(self):
        cases = (
            ("source_branch", lambda p, source: p.__setitem__("source_branch", source["source_branch"])),
            ("azure_devops.pipeline_yaml", lambda p, source: p["azure_devops"].__setitem__("pipeline_yaml", source["azure_devops"]["pipeline_yaml"])),
            ("azure_devops.protected_environment", lambda p, source: p["azure_devops"].__setitem__("protected_environment", source["azure_devops"]["protected_environment"])),
            ("workspace", lambda p, source: p.__setitem__("workspace", copy.deepcopy(source["workspace"]))),
        )
        for field, conflict in cases:
            with self.subTest(field=field):
                setup = self.profile_setup()
                setup["profiles"]["TEST2"] = copy.deepcopy(setup["profiles"]["TEST"])
                candidate = setup["profiles"]["TEST2"]
                candidate["source_branch"] = "test2"
                candidate["workspace"] = {"name": "WS TEST2", "id": "55555555-1111-4111-8111-111111111111", "create": False, "capacity": {"id": "cap", "name": "Cap"}}
                candidate["azure_devops"].update({"pipeline_name": "Repo Fabric TEST2", "pipeline_yaml": "cicd/fabric/fabric-test2.yml", "protected_environment": "fabric-test2"})
                conflict(setup["profiles"]["TEST2"], setup["profiles"]["DEV"])
                with self.assertRaisesRegex(ProfileError, "profile TEST2.*" + field.replace(".", r"\.")):
                    normalize_setup(setup)

    def test_runtime_loader_rejects_unconfigured_target(self):
        manifest = {"profiles": {"TEST2": {"workspace": {"id": "w", "name": "WS TEST2"}}}}
        self.assertEqual(("TEST2",), runtime_profiles.profile_keys(manifest))
        self.assertEqual("w", runtime_profiles.workspace(manifest, "TEST2")["id"])
        with self.assertRaisesRegex(SystemExit, "not configured"):
            runtime_profiles.workspace(manifest, "PROD")

    def test_branch_routing_supports_legacy_test2_and_uat_once_each(self):
        setup = self.profile_setup()
        for key, branch in (("TEST2", "test2"), ("UAT", "uat")):
            profile = copy.deepcopy(setup["profiles"]["TEST"])
            profile["source_branch"] = branch
            profile["workspace"] = {"name": f"WS {key}", "id": ("55555555" if key == "TEST2" else "66666666") + "-1111-4111-8111-111111111111", "create": False, "capacity": {"id": "cap", "name": "Cap"}}
            profile["azure_devops"].update({"pipeline_name": f"Repo Fabric {key}", "pipeline_yaml": f"cicd/fabric/fabric-{key.lower()}.yml", "protected_environment": f"fabric-{key.lower()}"})
            setup["profiles"][key] = profile
        for branch, expected in (("DEV", "DEV"), ("TEST", "TEST"), ("hotfix/FIN-1", "HOTFIX"), ("test2", "TEST2"), ("uat", "UAT")):
            self.assertEqual(expected, route_branch(setup, branch)[0])
        with self.assertRaisesRegex(ProfileError, "no profile"):
            route_branch(setup, "feature/x")

    def test_go_live_profile_is_a_normal_configured_profile(self):
        setup = self.profile_setup()
        profile = copy.deepcopy(setup["profiles"]["PROD"])
        profile["source_branch"] = "go-live"
        profile["workspace"] = {"name": "WS GO-LIVE", "id": "77777777-1111-4111-8111-111111111111", "create": False, "capacity": {"id": "cap", "name": "Cap"}}
        profile["azure_devops"].update({"pipeline_name": "Repo Fabric GO-LIVE", "pipeline_yaml": "cicd/fabric/fabric-go-live.yml", "protected_environment": "fabric-go-live"})
        profile["promotion"]["accepts_from"] = ["TEST"]
        setup["profiles"]["GO-LIVE"] = profile
        normalized = normalize_setup(setup)
        self.assertEqual("go-live", normalized["profiles"]["GO-LIVE"]["source_branch"])
        self.assertEqual(["TEST"], normalized["profiles"]["GO-LIVE"]["promotion"]["accepts_from"])


if __name__ == "__main__":
    unittest.main()
