# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `scripts/check_ruff_configs.py`, run in CI, fails when any Ruff config besides `ruff.toml` exists.
  It scans the current directory and skips the folders Ruff excludes by default.

### Changed

- `hardcoded-bind-all-interfaces` (S104), `hardcoded-temp-file` (S108) and
  `start-process-with-no-shell` (S606) now block: each fires far less than once per 1,000 lines.
  The register is 443 block, 191 warn, 318 off.
- `suspicious-non-cryptographic-random-usage` (S311) stays warn, with a reason that states why.
- The README's adoption commands and the pre-commit example pass `--ignore-noqa` to both tiers,
  matching CI.
- The pre-commit example pins `ruff-pre-commit` to the v0.16.9 commit instead of the tag.
- The CI job times out after 10 minutes.

### Fixed

- CI and the pre-commit example pass `--config ruff.toml`, so a nested `ruff.toml`, `.ruff.toml` or
  `pyproject.toml` can no longer replace the block tier. README adoption steps match.
- `requirements-dev.txt` pins Ruff's file hashes, and CI installs with `--require-hashes`.
- `render_register` writes valid TOML for any string, including emoji and DEL.
- `build_config.py` accepts only the register settings keys in `ALLOWED_SETTINGS`, so no setting
  can select, ignore or exclude a rule or file. This covers Ruff's deprecated top-level `ignore`
  and `per-file-ignores` aliases, `fix`, `format.exclude` and plugin options. `per-file-ignores`
  may name only warn or off rules.
- The `lint.pylint`, `lint.mccabe` and `lint.pydocstyle` settings tables accept only the options
  the register uses, instead of any option Ruff supports.
- A `.gitignore`, `.ignore` or `.git/info/exclude` entry can no longer hide a tracked file from the
  block tier or the format check: CI and the README's block-tier and format commands pass
  `--no-respect-gitignore`.
- `build_config.py` quotes a TOML key ending in a newline instead of writing invalid TOML.
- A `ruff: ignore[...]` comment can no longer hide a block finding in a repo that follows the
  adoption steps.
- Adoption step 2 keeps Ruff's hash pins and installs with `--require-hashes`.

## [0.1.0] - 2026-09-30

### Added

- `rules/register.toml` with a decision for all 952 selectable rules in Ruff 0.16.9:
  440 block, 194 warn, 318 off.
- Generated `ruff.toml` (block tier) and `ruff.warn.toml` (warn tier), selecting rules by name.
- `scripts/build_config.py` to validate the register and generate or drift-check the configs.
- `scripts/check_fixtures.py` and `fixtures/` to prove each tier reports what it should.
- CI workflow, pinned Ruff in `requirements-dev.txt`, and an example pre-commit config.
