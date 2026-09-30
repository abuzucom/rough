# rough

The organization's baseline [Ruff](https://docs.astral.sh/ruff/) configuration. Copy it into a
repo, then tailor it there.

## What is here

| Path | Purpose |
|---|---|
| `rules/register.toml` | Source of truth: one decision per Ruff rule, plus shared settings. |
| `ruff.toml` | Generated. Block rules: fail CI and pre-commit. |
| `ruff.warn.toml` | Generated. Warn rules: reported, never fail. Extends `ruff.toml`. |
| `scripts/build_config.py` | Validates the register and writes both configs. |
| `scripts/check_fixtures.py` | Proves the configs report exactly what `fixtures/` expects. |
| `scripts/check_ruff_configs.py` | Fails when any Ruff config besides `ruff.toml` exists. |
| `requirements-dev.txt` | Pins the Ruff version the register was decided against. |
| `examples/pre-commit-config.yaml` | Hooks to copy into an adopting repo. |

## How the rules were decided

Every one of the 952 selectable rules in Ruff 0.16.9 has a decision in the register:
440 block, 194 warn, 318 off.

- **Block** a rule when it catches real bugs, flags a security problem, or is hygiene that
  `ruff check --fix` resolves safely and that fires less than once per 1,000 lines.
- **Warn** on maintainability signals worth seeing but not worth failing a build: complexity
  and size limits, docstrings, type hints, commented-out code, TODO markers.
- **Off** for formatter conflicts, rules the google docstring convention excludes, and
  low-value style.

Noise was measured by running every rule over about 1.47 million lines from 12 mature
open-source projects (requests, flask, click, httpx, rich, attrs, pydantic, fastapi, django,
black, pytest, sqlalchemy). Each rule's `reason` in the register records why it landed where it
did.

The baseline targets code people write and review. Guidance aimed at coding agents lives in
AGENTS.md, not here.

Rules are selected by readable name (`unused-import`), not code (`F401`). `preview = true` is
required because some selected rules are still in preview.

## Adopt in a repo

1. Copy `ruff.toml` and `ruff.warn.toml` to the repo root.
2. Pin the same Ruff version: `ruff==0.16.9` in the repo's dev requirements.
3. Set `target-version` to the repo's minimum Python.
4. Tailor in place: move a rule between the two files' `select` lists, or delete it to turn it
   off. Adjust `per-file-ignores` for the repo's layout.
5. Run it in CI:

   ```sh
   python scripts/check_ruff_configs.py                    # no other Ruff config exists
   ruff check --config ruff.toml                           # block tier, fails the build
   ruff format --config ruff.toml --check
   ruff check --config ruff.warn.toml --exit-zero          # warn tier, report only
   ```

   Without `--config`, Ruff uses the nearest config for each file, so a `ruff.toml`,
   `.ruff.toml` or `pyproject.toml` with `[tool.ruff]` added anywhere in the tree would replace
   the baseline. Copy `scripts/check_ruff_configs.py` too; it fails when such a file exists.
   Add `--ignore-noqa` to the block-tier command to make suppression comments ineffective.
6. Optionally copy `examples/pre-commit-config.yaml` to `.pre-commit-config.yaml`.

## Change a decision here

1. Edit the rule's `status`, `autofix` or `reason` in `rules/register.toml`. An `off` rule
   needs a reason.
2. Run `python scripts/build_config.py` to regenerate both configs.
3. Run `python -m unittest` and `python scripts/check_fixtures.py`.
4. Commit the register and the generated files together. CI fails if they disagree.

## Upgrade Ruff

1. Bump the pin in `requirements-dev.txt` and install it.
2. Run `python scripts/build_config.py`. It lists every new rule as `undecided`, and every
   removed or renamed rule, and writes nothing until the register is fixed.
3. Decide each listed rule in the register, then rebuild.
4. Update `rev` in `examples/pre-commit-config.yaml` to match.

## What CI enforces in this repo

`.github/workflows/baseline.yml` runs on every pull request:

- The generated configs match the register (`build_config.py --check`).
- No Ruff config exists besides `ruff.toml` (`check_ruff_configs.py`).
- Unit tests pass (`python -m unittest`).
- Fixtures produce exactly the annotated findings (`check_fixtures.py`).
- The repo's own code passes the block tier with `--config ruff.toml --ignore-noqa`, and
  `ruff format --config ruff.toml --check`.
- The warn tier is reported but never fails.

## Ruff fork

[abuzucom/ruff](https://github.com/abuzucom/ruff) mirrors upstream
[astral-sh/ruff](https://github.com/astral-sh/ruff). The baseline uses upstream releases from
PyPI.
