"""Tests for scripts/check_fixtures.py."""

import pathlib
import shutil
import tempfile
import unittest

from tests.test_build_config import SETTINGS, build_config, load_script, make_rules

check_fixtures = load_script("check_fixtures")


class ParseExpectationsTest(unittest.TestCase):
    """parse_expectations reads `# expect:` and `# expect-warn:` trailing comments."""

    def test_reads_both_tiers_and_multiple_names(self) -> None:
        """Each tag maps to its tier; comma-separated names all count."""
        source = "import os  # expect: unused-import\nx = 1  # expect-warn: a-rule, b-rule\ny = 2\n"
        expected = check_fixtures.parse_expectations(source)
        self.assertEqual(expected["block"], {(1, "unused-import")})
        self.assertEqual(expected["warn"], {(2, "a-rule"), (2, "b-rule")})


class CompareTest(unittest.TestCase):
    """compare_findings reports both missing and unexpected findings."""

    def test_missing_and_unexpected_are_reported(self) -> None:
        """A finding that should fire but did not, and one that fired unasked, both fail."""
        problems = check_fixtures.compare_findings("f.py", "block", {(1, "a"), (2, "b")}, {(2, "b"), (3, "c")})
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("f.py:1" in p and "missing" in p and "a" in p for p in problems), problems)
        self.assertTrue(any("f.py:3" in p and "unexpected" in p and "c" in p for p in problems), problems)

    def test_exact_match_has_no_problems(self) -> None:
        """Identical sets pass."""
        self.assertEqual(check_fixtures.compare_findings("f.py", "warn", {(1, "a")}, {(1, "a")}), [])


@unittest.skipUnless(shutil.which("ruff"), "ruff is not installed")
class MainTest(unittest.TestCase):
    """main runs both configs over the fixtures with the real Ruff."""

    def setUp(self) -> None:
        """Lay out configs from the sample register plus one violation and one clean fixture."""
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        rules = make_rules()
        (self.root / "ruff.toml").write_text(build_config.render_block_config(SETTINGS, rules), encoding="utf-8")
        (self.root / "ruff.warn.toml").write_text(build_config.render_warn_config(rules), encoding="utf-8")
        (self.root / "fixtures" / "violations").mkdir(parents=True)
        (self.root / "fixtures" / "clean").mkdir(parents=True)
        long_value = repr("x" * 130)
        self.violation = self.root / "fixtures" / "violations" / "sample.py"
        self.violation.write_text(
            f"import os  # expect: unused-import\nVALUE = {long_value}  # expect-warn: line-too-long\n",
            encoding="utf-8",
        )
        (self.root / "fixtures" / "clean" / "ok.py").write_text('"""Clean."""\n', encoding="utf-8")

    def test_passes_when_expectations_match(self) -> None:
        """Correct annotations pass."""
        self.assertEqual(check_fixtures.main(["--root", str(self.root)]), 0)

    def test_fails_when_block_rule_does_not_fire(self) -> None:
        """An expected block finding that Ruff does not report fails the check."""
        text = self.violation.read_text(encoding="utf-8").replace("import os  #", "import os\nos.getcwd()  #")
        self.violation.write_text(text, encoding="utf-8")
        self.assertEqual(check_fixtures.main(["--root", str(self.root)]), 1)

    def test_fails_when_clean_fixture_has_findings(self) -> None:
        """Any finding in a clean fixture fails the check."""
        (self.root / "fixtures" / "clean" / "ok.py").write_text('"""Clean."""\n\nimport os\n', encoding="utf-8")
        self.assertEqual(check_fixtures.main(["--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
