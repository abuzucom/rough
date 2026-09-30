"""Check that ruff.toml and ruff.warn.toml report exactly what the fixtures expect.

fixtures/violations/*.py mark each expected finding with a trailing comment:
  # expect: rule-name[, rule-name]        reported by ruff.toml (block)
  # expect-warn: rule-name[, rule-name]   reported by ruff.warn.toml (warn)
Any finding without a matching comment, or comment without a finding, fails.
fixtures/clean/*.py must produce no findings under either config.

Usage:
  python scripts/check_fixtures.py
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys

TIERS = {"block": "ruff.toml", "warn": "ruff.warn.toml"}
EXPECT = re.compile(r"#\s*expect(?P<warn>-warn)?:\s*(?P<names>[a-z0-9, -]+)$")


def parse_expectations(source: str) -> dict[str, set[tuple[int, str]]]:
    """Return the expected (line, rule-name) pairs per tier from `# expect` comments.

    Returns:
        A mapping from tier ("block" or "warn") to its expected findings.
    """
    expected = {tier: set() for tier in TIERS}
    for number, line in enumerate(source.splitlines(), start=1):
        match = EXPECT.search(line)
        if match:
            tier = "warn" if match["warn"] else "block"
            expected[tier].update((number, name.strip()) for name in match["names"].split(",") if name.strip())
    return expected


def run_ruff(root: pathlib.Path, config: str, path: pathlib.Path) -> set[tuple[int, str]]:
    """Return the (line, rule-name) findings Ruff reports for one file.

    Returns:
        Every finding, with suppression comments ignored.
    """
    result = subprocess.run(
        [
            "ruff",
            "check",
            "--config",
            config,
            "--ignore-noqa",
            "--no-cache",
            "--exit-zero",
            "--output-format",
            "json",
            str(path),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return {(d["location"]["row"], d["name"]) for d in json.loads(result.stdout)}


def compare_findings(label: str, tier: str, expected: set, actual: set) -> list[str]:
    """Describe every difference between expected and actual findings.

    Returns:
        One message per missing or unexpected finding.
    """
    missing = [f"{label}:{line}: [{tier}] missing {name}" for line, name in sorted(expected - actual)]
    unexpected = [f"{label}:{line}: [{tier}] unexpected {name}" for line, name in sorted(actual - expected)]
    return missing + unexpected


def check_file(root: pathlib.Path, path: pathlib.Path, *, clean: bool) -> list[str]:
    """Run both tiers on one fixture and compare with its expectations.

    Returns:
        The problems found in this fixture.
    """
    label = path.relative_to(root).as_posix()
    expected = parse_expectations(path.read_text(encoding="utf-8"))
    problems = []
    for tier, config in TIERS.items():
        wanted = set() if clean else expected[tier]
        problems.extend(compare_findings(label, tier, wanted, run_ruff(root, config, path)))
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check every fixture and report problems.

    Returns:
        0 when every fixture matches, else 1.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    fixtures = args.root / "fixtures"
    problems = []
    for path in sorted((fixtures / "violations").glob("*.py")):
        problems.extend(check_file(args.root, path, clean=False))
    for path in sorted((fixtures / "clean").glob("*.py")):
        problems.extend(check_file(args.root, path, clean=True))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"{len(problems)} fixture mismatch(es). Fix the config or the fixture annotations.", file=sys.stderr)
        return 1
    print("All fixtures match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
