# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project

`digital-land-qa-agent` — a multi-agent QA automation framework that points at other digital-land repos and generates tests, runs checks, and produces audit artifacts. Python 3.10+, installs as the `dl-qa` CLI.

It is itself an *agentic* application built on the Anthropic SDK; this repo's code calls Claude. When editing here, keep that distinction in mind: there is a difference between the agent we're building (`digital_land_qa_agent/`) and any code we're generating *for* a target repo.

## Common commands

```bash
make dev          # editable install with dev extras (pytest, ruff)
make test         # pytest
make lint         # ruff check src tests
make demo         # runs `dl-qa run --target pyspark-jobs ...`
make clean        # wipes runs/, caches, egg-info
```

CLI entrypoint: `dl-qa` → `digital_land_qa_agent.__main__:cli`. Subcommands:
- `dl-qa list-targets` — show configured targets
- `dl-qa profile --target <name>` — run only the Profiler stage
- `dl-qa run --target <name> --goal "<goal>"` — full pipeline against one goal
- `dl-qa diff --target <name> --base <ref> [--head <ref>] [--files <path>...]` — run the pipeline against every changed source file (used by the GitHub Action)
- `dl-qa metrics` — aggregate observability across every `runs/<ts>/` (approval rate, revisions, tokens)

All commands accept `--target-path <dir>` to override the configured target path (used by the GitHub Action to point at `$GITHUB_WORKSPACE`).

## GitHub Action

The repo's [action.yml](action.yml) at the root makes it consumable as a composite GitHub Action. The intended consumer pattern (see [examples/pyspark-jobs-qa-agent.yml](examples/pyspark-jobs-qa-agent.yml)):
1. Target repo's workflow fires on push to a branch and `paths: src/**/*.py`.
2. Workflow checks out target + this action.
3. Action runs `dl-qa diff` against the changed files.
4. Staged tests are copied into a PR branch via `peter-evans/create-pull-request`.
5. A human reviews. Never auto-merge.

## Layout

- [digital_land_qa_agent/](digital_land_qa_agent/) — package root
  - [__main__.py](digital_land_qa_agent/__main__.py) — Click CLI: `dl-qa run / list-targets / profile`
  - [config.py](digital_land_qa_agent/config.py) — `Settings` (global) + `TargetConfig` (per-repo) loaders
  - [orchestrator.py](digital_land_qa_agent/orchestrator.py) — sequential pipeline + `PipelineResult`
  - [runs.py](digital_land_qa_agent/runs.py) — per-run staging dir + JSONL audit log
  - [metrics.py](digital_land_qa_agent/metrics.py) — cross-run rollup feeding `dl-qa metrics`
  - `agents/` — `ProfilerAgent`, `PlannerAgent`, `TestWriterAgent`, `CriticAgent` (all extend `agents.base.BaseAgent`)
  - `llm/` — `client.LiveClient` (Anthropic SDK) + `mock.MockClient` (deterministic fixtures); `build_client()` picks based on `ANTHROPIC_API_KEY`
  - `llm/fixtures.py` — pre-canned content blocks the mock returns, keyed by agent name
  - `tools/` — `fs.{list_files,read_file,write_staged_test}` (sandboxed) and `runners.{run_ruff,run_python_compile,run_pytest_collect}`
  - `prompts/` — one `<agent>.md` per agent, loaded by `BaseAgent.system_prompt`
- [config/settings.yaml](config/settings.yaml) — global agent settings (model, thinking, effort, budgets, HITL)
- [config/targets/](config/targets/) — one YAML per target repo; copy `_template.yaml` to add a new one
- `tests/` — pytest suite (testpaths set in pyproject.toml); includes an end-to-end pipeline test that requires `~/repos/pyspark-jobs` (skips otherwise)
- `runs/` — per-run artifacts and audit logs (gitignored)

## Agent pipeline

```
ProfilerAgent  →  PlannerAgent  →  TestWriterAgent  →  CriticAgent (loops up to 3x)
   profile          test plan         staged file       verdict + static checks
```

Each agent has its own system prompt under `prompts/`. The orchestrator passes structured JSON between stages and writes every artifact (`profile.json`, `plan.json`, `critic_verdict.json`) plus a JSONL audit log under `runs/<ts>/`.

## Critic gates

Approval requires **all** of:
- LLM verdict == `approved`
- `python -m py_compile` clean
- every command in the target's `lint_commands` exits 0

Lint commands are declared per target in `config/targets/<name>.yaml`. The Critic runs each command with `cwd=<target_root>` so the linter picks up the target's own config files (`.flake8`, `.isort.cfg`, `pyproject.toml`). The framework itself does not hardcode a linter — `pyspark-jobs` uses black + flake8 + isort; a different target could use ruff, eslint, etc.

`pytest --collect-only` is run for information but does **not** gate approval — the target repo's runtime deps (pyspark, sedona, etc.) are usually not installed in this venv, so the real collect happens when the staged test is moved to the target.

To run the pyspark-jobs demo locally, install the optional target-python extras alongside dev: `pip install -e ".[dev,targets-python]"`.

## Defaults you should preserve

From [config/settings.yaml](config/settings.yaml):

- Model: `claude-opus-4-7`
- `thinking: adaptive`, `effort: xhigh` (recommended for Opus 4.7 agentic loops)
- `task_budget_tokens: 200000`, `max_tokens: 64000`, `max_tool_rounds: 12`
- `hitl_required: true` — **human approval required before any file is written or test is committed to a target repo.** Do not bypass this without explicit user instruction.

Env overrides (see [.env.example](.env.example)): `ANTHROPIC_API_KEY`, `DL_QA_MODEL`, `DL_QA_TASK_BUDGET_TOKENS`, `DL_QA_RUNS_DIR`. With `ANTHROPIC_API_KEY` unset the agent runs in deterministic mock mode.

## Conventions

- Ruff: line length 100, target Py 3.10.
- Use `from __future__ import annotations` (see config.py) and dataclasses for structured config.
- Paths via `pathlib.Path`, not strings.
- New target repos: copy `config/targets/_template.yaml` — most fields are auto-detected by the profiler if omitted.

## Notes

This file is for Claude Code's benefit. Update it when project shape or defaults change; don't let it drift.
