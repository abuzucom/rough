"""Tests for scripts/build_config.py."""

import copy
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from types import ModuleType

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_script(name: str) -> ModuleType:
    """Import scripts/<name>.py by path; scripts/ is a folder of tools, not a package.

    Returns:
        The imported module.
    """
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_config = load_script("build_config")

CATALOG = {
    "F401": {"name": "unused-import", "fix": "Sometimes"},
    "E501": {"name": "line-too-long", "fix": "None"},
    "ERA001": {"name": "commented-out-code", "fix": "None"},
    "Q000": {"name": "bad-quotes-inline-string", "fix": "Sometimes"},
}
SETTINGS = {
    "line-length": 120,
    "target-version": "py312",
    "preview": True,
    "lint": {"pylint": {"max-args": 5}, "per-file-ignores": {"tests/**": ["line-too-long"]}},
    "format": {"quote-style": "double"},
}


# Settings keys that Ruff 0.16.9 accepts and that would override a register decision. Top-level
# select, ignore and per-file-ignores are deprecated aliases Ruff still applies.
BYPASS_KEYS = (
    "extend",
    "include",
    "extend-include",
    "exclude",
    "extend-exclude",
    "fix",
    "unsafe-fixes",
    "builtins",
    "select",
    "extend-select",
    "ignore",
    "extend-ignore",
    "per-file-ignores",
    "extend-per-file-ignores",
    "lint.select",
    "lint.extend-select",
    "lint.ignore",
    "lint.extend-ignore",
    "lint.fixable",
    "lint.extend-fixable",
    "lint.unfixable",
    "lint.extend-safe-fixes",
    "lint.extend-unsafe-fixes",
    "lint.extend-per-file-ignores",
    "lint.exclude",
    "lint.flake8-bandit",
    "format.exclude",
)


def make_rules() -> list[dict]:
    """Return a valid register covering every status and the no-autofix flag."""
    return [
        {"code": "F401", "name": "unused-import", "status": "block", "autofix": False, "reason": "Bugs."},
        {"code": "E501", "name": "line-too-long", "status": "warn", "autofix": True, "reason": "Style."},
        {"code": "ERA001", "name": "commented-out-code", "status": "warn", "autofix": False, "reason": "Dead code."},
        {
            "code": "Q000",
            "name": "bad-quotes-inline-string",
            "status": "off",
            "autofix": True,
            "reason": "Formatter owns quotes.",
        },
    ]


class ValidateRegisterTest(unittest.TestCase):
    """validate_register reports every way a register can disagree with the catalog."""

    def test_valid_register_has_no_errors(self) -> None:
        """A complete, consistent register validates cleanly."""
        self.assertEqual(build_config.validate_register(make_rules(), CATALOG), [])

    def test_rule_missing_from_register_is_undecided(self) -> None:
        """A catalog rule with no register entry is reported as undecided."""
        rules = [r for r in make_rules() if r["code"] != "E501"]
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("E501" in e and "undecided" in e for e in errors), errors)

    def test_unknown_code_is_reported(self) -> None:
        """A register entry Ruff does not know is reported."""
        rules = [
            *make_rules(),
            {"code": "XYZ999", "name": "made-up", "status": "block", "autofix": True, "reason": "x"},
        ]
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("XYZ999" in e and "unknown" in e for e in errors), errors)

    def test_duplicate_code_is_reported(self) -> None:
        """The same code listed twice is reported."""
        rules = [*make_rules(), make_rules()[0]]
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("F401" in e and "duplicate" in e for e in errors), errors)

    def test_off_without_reason_is_reported(self) -> None:
        """An off rule must say why."""
        rules = make_rules()
        rules[3]["reason"] = "  "
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("Q000" in e and "reason" in e for e in errors), errors)

    def test_invalid_status_is_reported(self) -> None:
        """Only block, warn and off are accepted."""
        rules = make_rules()
        rules[0]["status"] = "error"
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("F401" in e and "status" in e for e in errors), errors)

    def test_name_mismatch_is_reported(self) -> None:
        """A stale rule name (renamed upstream) is reported."""
        rules = make_rules()
        rules[0]["name"] = "old-name"
        errors = build_config.validate_register(rules, CATALOG)
        self.assertTrue(any("F401" in e and "name" in e for e in errors), errors)


class ValidateSettingsTest(unittest.TestCase):
    """validate_settings rejects settings that would override the register's rule decisions."""

    def errors_for(self, settings: dict) -> list[str]:
        """Return the settings errors against the sample register and catalog.

        Returns:
            The problems validate_settings reports.
        """
        return build_config.validate_settings(settings, make_rules(), CATALOG)

    def with_ignores(self, selectors: list[str]) -> dict:
        """Return SETTINGS with the given per-file-ignores selectors for every file.

        Returns:
            A modified copy of SETTINGS.
        """
        settings = copy.deepcopy(SETTINGS)
        settings["lint"]["per-file-ignores"] = {"**": selectors}
        return settings

    def test_valid_settings_have_no_errors(self) -> None:
        """Settings that only tune rules validate cleanly."""
        self.assertEqual(self.errors_for(SETTINGS), [])

    def test_known_bypass_keys_are_reported(self) -> None:
        """Every key shown to select, ignore, fix or exclude outside the register is rejected."""
        for path in BYPASS_KEYS:
            with self.subTest(key=path):
                settings = copy.deepcopy(SETTINGS)
                *tables, key = path.split(".")
                target = settings
                for table in tables:
                    target = target.setdefault(table, {})
                target[key] = ["S602"]
                errors = self.errors_for(settings)
                self.assertTrue(any(f"settings: {path} " in e and "not allowed" in e for e in errors), errors)

    def test_unknown_option_in_allowed_table_is_reported(self) -> None:
        """An allowed table accepts only its listed options, not any key Ruff supports."""
        for table in ("pylint", "mccabe", "pydocstyle"):
            with self.subTest(table=table):
                settings = copy.deepcopy(SETTINGS)
                settings["lint"].setdefault(table, {})["future-option"] = True
                errors = self.errors_for(settings)
                path = f"settings: lint.{table}.future-option "
                self.assertTrue(any(path in e and "not allowed" in e for e in errors), errors)

    def test_unknown_key_is_reported(self) -> None:
        """A key outside the allowlist fails even when it is not a known bypass."""
        settings = copy.deepcopy(SETTINGS)
        settings["lint"]["future-ruff-option"] = True
        errors = self.errors_for(settings)
        self.assertTrue(any("lint.future-ruff-option" in e and "not allowed" in e for e in errors), errors)

    def test_per_file_ignores_must_use_known_rule_names(self) -> None:
        """Codes, prefixes, ALL and unknown names cannot be per-file ignored."""
        for selector in ("E501", "S", "ALL", "made-up-rule"):
            with self.subTest(selector=selector):
                errors = self.errors_for(self.with_ignores([selector]))
                self.assertTrue(any(repr(selector) in e and "rule name" in e for e in errors), errors)

    def test_per_file_ignores_cannot_name_block_rules(self) -> None:
        """A block rule must fire everywhere, so per-file-ignores cannot name one."""
        errors = self.errors_for(self.with_ignores(["unused-import"]))
        self.assertTrue(any("unused-import" in e and "block" in e for e in errors), errors)

    def test_per_file_ignores_may_name_warn_and_off_rules(self) -> None:
        """Warn and off rules may be ignored per file."""
        self.assertEqual(self.errors_for(self.with_ignores(["line-too-long", "bad-quotes-inline-string"])), [])


class RenderConfigTest(unittest.TestCase):
    """render_block_config and render_warn_config place each rule in the right file."""

    def setUp(self) -> None:
        """Render both configs from the sample register."""
        self.block = tomllib.loads(build_config.render_block_config(SETTINGS, make_rules()))
        self.warn = tomllib.loads(build_config.render_warn_config(make_rules()))

    def test_block_rule_selected_only_in_block_config(self) -> None:
        """Block rules are selected by name in ruff.toml and absent from the warn config."""
        self.assertEqual(self.block["lint"]["select"], ["unused-import"])
        self.assertNotIn("unused-import", self.warn["lint"]["select"])

    def test_warn_rule_selected_only_in_warn_config(self) -> None:
        """Warn rules are selected in ruff.warn.toml, which extends ruff.toml."""
        self.assertEqual(self.warn["lint"]["select"], ["commented-out-code", "line-too-long"])
        self.assertEqual(self.warn["extend"], "ruff.toml")

    def test_off_rule_selected_nowhere(self) -> None:
        """Off rules appear in neither config."""
        self.assertNotIn("bad-quotes-inline-string", self.block["lint"]["select"])
        self.assertNotIn("bad-quotes-inline-string", self.warn["lint"]["select"])

    def test_no_autofix_rules_are_unfixable(self) -> None:
        """No-autofix rules from both tiers land in lint.unfixable; off rules do not."""
        self.assertEqual(self.block["lint"]["unfixable"], ["commented-out-code", "unused-import"])

    def test_settings_are_emitted(self) -> None:
        """Register settings pass through to ruff.toml unchanged."""
        self.assertEqual(self.block["line-length"], 120)
        self.assertIs(self.block["preview"], True)
        self.assertEqual(self.block["lint"]["pylint"]["max-args"], 5)
        self.assertEqual(self.block["lint"]["per-file-ignores"], {"tests/**": ["line-too-long"]})
        self.assertEqual(self.block["format"]["quote-style"], "double")

    def test_generated_header_present(self) -> None:
        """Both files say they are generated."""
        for text in (
            build_config.render_block_config(SETTINGS, make_rules()),
            build_config.render_warn_config(make_rules()),
        ):
            self.assertTrue(text.startswith("# Generated by scripts/build_config.py"))


class RenderRegisterTest(unittest.TestCase):
    """render_register writes TOML that reads back to the same data."""

    def test_any_string_round_trips(self) -> None:
        """Emoji, DEL and other characters survive in values and quoted keys."""
        reason = 'Emoji \U0001f600, DEL \x7f, tab \t, quote ", backslash \\, e-acute \u00e9.'
        rules = make_rules()
        rules[0]["reason"] = reason
        settings = copy.deepcopy(SETTINGS)
        settings["lint"]["per-file-ignores"]["caf\u00e9/\U0001f600/**"] = ["assert"]
        register = tomllib.loads(build_config.render_register(settings, rules))
        reasons = {rule["code"]: rule["reason"] for rule in register["rule"]}
        self.assertEqual(reasons["F401"], reason)
        self.assertEqual(register["settings"], settings)

    def test_key_with_trailing_newline_round_trips(self) -> None:
        """A key that is bare except for a trailing newline is quoted, not written raw."""
        settings = copy.deepcopy(SETTINGS)
        settings["lint"]["per-file-ignores"]["tests\n"] = ["line-too-long"]
        register = tomllib.loads(build_config.render_register(settings, make_rules()))
        self.assertEqual(register["settings"], settings)


class CheckModeTest(unittest.TestCase):
    """main --check detects generated files that drifted from the register."""

    def setUp(self) -> None:
        """Create a temporary repo layout with a register and a catalog file."""
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "rules").mkdir()
        register = build_config.render_register(SETTINGS, make_rules())
        (self.tmp / "rules" / "register.toml").write_text(register, encoding="utf-8")
        self.catalog_path = self.tmp / "catalog.json"
        self.catalog_path.write_text(json.dumps(CATALOG), encoding="utf-8")

    def run_main(self, *extra: str) -> int:
        """Run main against the temporary layout.

        Returns:
            The exit code from main.
        """
        return build_config.main(["--root", str(self.tmp), "--catalog", str(self.catalog_path), *extra])

    def test_check_passes_after_build(self) -> None:
        """A fresh build is not reported as drift."""
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.run_main("--check"), 0)

    def test_check_fails_on_hand_edit(self) -> None:
        """Editing a generated file by hand is reported as drift."""
        self.assertEqual(self.run_main(), 0)
        target = self.tmp / "ruff.toml"
        target.write_text(target.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
        self.assertEqual(self.run_main("--check"), 1)

    def test_invalid_register_fails_without_writing(self) -> None:
        """An undecided rule fails the build and writes nothing."""
        partial = [r for r in make_rules() if r["code"] != "E501"]
        register = build_config.render_register(SETTINGS, partial)
        (self.tmp / "rules" / "register.toml").write_text(register, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)
        self.assertFalse((self.tmp / "ruff.toml").exists())

    def test_overriding_settings_fail_without_writing(self) -> None:
        """Settings that ignore a block rule fail the build and write nothing."""
        settings = copy.deepcopy(SETTINGS)
        settings["lint"]["ignore"] = ["unused-import"]
        register = build_config.render_register(settings, make_rules())
        (self.tmp / "rules" / "register.toml").write_text(register, encoding="utf-8")
        self.assertEqual(self.run_main(), 1)
        self.assertFalse((self.tmp / "ruff.toml").exists())


@unittest.skipUnless(shutil.which("ruff"), "ruff is not installed")
class RealRuffTest(unittest.TestCase):
    """The generated configs behave as intended under the pinned Ruff."""

    def setUp(self) -> None:
        """Build configs for the sample register next to a file with one block and one warn hit."""
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "ruff.toml").write_text(build_config.render_block_config(SETTINGS, make_rules()), encoding="utf-8")
        (self.tmp / "ruff.warn.toml").write_text(build_config.render_warn_config(make_rules()), encoding="utf-8")
        long_line = "VALUE = " + repr("x" * 130) + "\n"
        (self.tmp / "sample.py").write_text("import os\n" + long_line, encoding="utf-8")

    def run_ruff(self, config: str) -> set[str]:
        """Return the rule names Ruff reports on the sample with the given config."""
        result = subprocess.run(
            ["ruff", "check", "--no-cache", "--exit-zero", "--output-format", "json", "--config", config, "sample.py"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
            check=True,
        )
        return {d["name"] for d in json.loads(result.stdout)}

    def test_block_config_reports_only_block_rules(self) -> None:
        """ruff.toml reports the unused import but not the long line."""
        self.assertEqual(self.run_ruff("ruff.toml"), {"unused-import"})

    def test_warn_config_reports_only_warn_rules(self) -> None:
        """ruff.warn.toml reports the long line but not the unused import."""
        self.assertEqual(self.run_ruff("ruff.warn.toml"), {"line-too-long"})


if __name__ == "__main__":
    unittest.main()
