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

### Fixed

- CI and the pre-commit example pass `--config ruff.toml`, so a nested `ruff.toml`, `.ruff.toml` or
  `pyproject.toml` can no longer replace the block tier. README adoption steps match.
- `requirements-dev.txt` pins Ruff's file hashes, and CI installs with `--require-hashes`.
- `render_register` writes valid TOML for any string, including emoji and DEL.

## [0.1.0] - 2026-09-30

### Added

- `rules/register.toml` with a decision for all 952 selectable rules in Ruff 0.16.9:
  440 block, 194 warn, 318 off.
- Generated `ruff.toml` (block tier) and `ruff.warn.toml` (warn tier), selecting rules by name.
- `scripts/build_config.py` to validate the register and generate or drift-check the configs.
- `scripts/check_fixtures.py` and `fixtures/` to prove each tier reports what it should.
- CI workflow, pinned Ruff in `requirements-dev.txt`, and an example pre-commit config.
