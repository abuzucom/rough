"""Tests that the adoption instructions keep the baseline's protections."""

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
PRE_COMMIT_EXAMPLE = REPO_ROOT / "examples" / "pre-commit-config.yaml"
RUFF_CHECK_LINE = re.compile(r"^\s*ruff check\b")


def read_text(path: pathlib.Path) -> str:
    """Return a repository file's text.

    Returns:
        The file contents.
    """
    return path.read_text(encoding="utf-8")


def pre_commit_hooks(hook_id: str) -> list[str]:
    """Return the text of each hook in the pre-commit example with the given id.

    Returns:
        One string per matching hook, from its id up to the next hook.
    """
    chunks = read_text(PRE_COMMIT_EXAMPLE).split("- id:")[1:]
    return [chunk for chunk in chunks if chunk.split()[0] == hook_id]


class AdoptionDocsTest(unittest.TestCase):
    """README and the pre-commit example run the baseline the way CI does."""

    def test_readme_ruff_check_commands_ignore_suppressions(self) -> None:
        """Every `ruff check` command in the README passes --ignore-noqa."""
        commands = [line for line in read_text(README).splitlines() if RUFF_CHECK_LINE.match(line)]
        self.assertTrue(commands, "README has no ruff check command")
        for command in commands:
            with self.subTest(command=command.strip()):
                self.assertIn("--ignore-noqa", command)

    def test_pre_commit_ruff_check_hooks_ignore_suppressions(self) -> None:
        """Every ruff-check hook in the pre-commit example passes --ignore-noqa."""
        hooks = pre_commit_hooks("ruff-check")
        self.assertTrue(hooks, "pre-commit example has no ruff-check hook")
        for hook in hooks:
            with self.subTest(hook=hook.strip().splitlines()[-1]):
                args = [line for line in hook.splitlines() if line.strip().startswith("args:")]
                self.assertEqual(len(args), 1, hook)
                self.assertIn("--ignore-noqa", args[0])


@unittest.skipUnless(shutil.which("ruff"), "ruff is not installed")
class IgnoreNoqaTest(unittest.TestCase):
    """--ignore-noqa reports findings that a `ruff: ignore` comment would hide."""

    def setUp(self) -> None:
        """Create a config selecting unused-import and a file suppressing its one hit."""
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "ruff.toml").write_text('preview = true\nlint.select = ["unused-import"]\n', encoding="utf-8")
        (self.tmp / "sample.py").write_text("import os  # ruff: ignore[unused-import]\n", encoding="utf-8")

    def run_ruff(self, *options: str) -> set[str]:
        """Return the rule names Ruff reports on the sample with the given options."""
        result = subprocess.run(
            [
                "ruff",
                "check",
                "--no-cache",
                "--exit-zero",
                "--output-format",
                "json",
                "--config",
                "ruff.toml",
                *options,
            ],
            cwd=self.tmp,
            capture_output=True,
            text=True,
            check=True,
        )
        return {d["name"] for d in json.loads(result.stdout)}

    def test_comment_hides_finding_without_flag(self) -> None:
        """Without --ignore-noqa the suppression comment hides the finding."""
        self.assertEqual(self.run_ruff(), set())

    def test_flag_reports_suppressed_finding(self) -> None:
        """With --ignore-noqa the finding is reported despite the comment."""
        self.assertEqual(self.run_ruff("--ignore-noqa"), {"unused-import"})


if __name__ == "__main__":
    unittest.main()
