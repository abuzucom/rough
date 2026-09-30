"""Tests for scripts/check_ruff_configs.py."""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.test_build_config import load_script

check_ruff_configs = load_script("check_ruff_configs")

STRAY_CONFIG = "lint.select = []\n"


class FindStrayConfigsTest(unittest.TestCase):
    """find_stray_configs reports every Ruff config other than the root ruff.toml."""

    def setUp(self) -> None:
        """Create a temporary repo root holding only the baseline ruff.toml."""
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "ruff.toml").write_text('lint.select = ["F401"]\n', encoding="utf-8")
        (self.tmp / "ruff.warn.toml").write_text('extend = "ruff.toml"\n', encoding="utf-8")

    def write(self, relative: str, text: str) -> None:
        """Write a file under the temporary root, creating its parent directories."""
        path = self.tmp / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def stray(self) -> list[str]:
        """Return the stray config paths, relative to the root, as POSIX strings."""
        return [p.relative_to(self.tmp).as_posix() for p in check_ruff_configs.find_stray_configs(self.tmp)]

    def test_baseline_files_alone_pass(self) -> None:
        """The root ruff.toml and ruff.warn.toml are not stray."""
        self.assertEqual(self.stray(), [])

    def test_nested_ruff_toml_is_stray(self) -> None:
        """A ruff.toml below the root overrides the baseline for that directory."""
        self.write("scripts/ruff.toml", STRAY_CONFIG)
        self.assertEqual(self.stray(), ["scripts/ruff.toml"])

    def test_dot_ruff_toml_is_stray_anywhere(self) -> None:
        """A .ruff.toml outranks ruff.toml, at the root or below it."""
        self.write(".ruff.toml", STRAY_CONFIG)
        self.write("tests/.ruff.toml", STRAY_CONFIG)
        self.assertEqual(self.stray(), [".ruff.toml", "tests/.ruff.toml"])

    def test_pyproject_with_tool_ruff_is_stray(self) -> None:
        """A pyproject.toml with a [tool.ruff] table is a Ruff config."""
        self.write("pkg/pyproject.toml", "[tool.ruff]\n" + STRAY_CONFIG)
        self.assertEqual(self.stray(), ["pkg/pyproject.toml"])

    def test_pyproject_without_tool_ruff_passes(self) -> None:
        """A pyproject.toml that never mentions Ruff is not a Ruff config."""
        self.write("pyproject.toml", '[project]\nname = "demo"\n')
        self.assertEqual(self.stray(), [])

    def test_unparsable_pyproject_is_stray(self) -> None:
        """A pyproject.toml the checker cannot read is reported rather than trusted."""
        self.write("pyproject.toml", "[tool.ruff\n")
        self.assertEqual(self.stray(), ["pyproject.toml"])

    def test_git_directory_is_skipped(self) -> None:
        """Files under .git are not part of the checked tree."""
        self.write(".git/ruff.toml", STRAY_CONFIG)
        self.assertEqual(self.stray(), [])

    def test_ruff_default_excludes_are_skipped(self) -> None:
        """Ruff never reads configs in its default-excluded folders, at any depth."""
        self.write(".venv/lib/pkg/pyproject.toml", "[tool.ruff]\n" + STRAY_CONFIG)
        self.write("web/node_modules/pkg/ruff.toml", STRAY_CONFIG)
        self.assertEqual(self.stray(), [])

    def test_build_directory_is_checked(self) -> None:
        """A build folder is not in Ruff's default excludes, so a config there still counts."""
        self.write("build/ruff.toml", STRAY_CONFIG)
        self.assertEqual(self.stray(), ["build/ruff.toml"])

    def test_non_table_tool_is_stray(self) -> None:
        """A pyproject.toml whose tool key is not a table is reported, not a crash."""
        self.write("pyproject.toml", "tool = 1\n")
        self.assertEqual(self.stray(), ["pyproject.toml"])

    def test_main_exit_codes(self) -> None:
        """The exit code is 0 for a clean tree and 1 once a stray config appears."""
        self.assertEqual(check_ruff_configs.main(["--root", str(self.tmp)]), 0)
        self.write("scripts/ruff.toml", STRAY_CONFIG)
        self.assertEqual(check_ruff_configs.main(["--root", str(self.tmp)]), 1)

    def test_root_defaults_to_current_directory(self) -> None:
        """Without --root the check scans the working directory, wherever the script lives."""
        self.write(".ruff.toml", STRAY_CONFIG)
        self.addCleanup(os.chdir, pathlib.Path.cwd())
        os.chdir(self.tmp)
        self.assertEqual(check_ruff_configs.main([]), 1)


@unittest.skipUnless(shutil.which("ruff"), "ruff is not installed")
class RealRuffTest(unittest.TestCase):
    """--config ruff.toml keeps a stray config from disabling the block tier."""

    def setUp(self) -> None:
        """Create a root config that selects unused-import, a stray config that selects nothing, and a hit."""
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "ruff.toml").write_text('lint.select = ["F401"]\n', encoding="utf-8")
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "ruff.toml").write_text(STRAY_CONFIG, encoding="utf-8")
        (self.tmp / "src" / "sample.py").write_text("import os\n", encoding="utf-8")

    def run_ruff(self, *options: str) -> int:
        """Run `ruff check` on src with the given options.

        Returns:
            Ruff's exit code.
        """
        result = subprocess.run(
            ["ruff", "check", "--no-cache", *options, "src"],
            cwd=self.tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode

    def test_stray_config_wins_without_config_flag(self) -> None:
        """Hierarchical discovery lets the stray config hide the finding."""
        self.assertEqual(self.run_ruff(), 0)

    def test_config_flag_keeps_the_finding(self) -> None:
        """With --config ruff.toml the finding is still reported."""
        self.assertEqual(self.run_ruff("--config", "ruff.toml"), 1)


if __name__ == "__main__":
    unittest.main()
