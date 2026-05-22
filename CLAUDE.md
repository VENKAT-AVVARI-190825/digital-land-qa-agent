# CLAUDE.md

Guidance for Claude Code when working in this repo.

## Project

`digital-land-qa-agent` — a multi-agent QA automation framework that points at other digital-land repos and generates tests, runs checks, and produces audit artifacts. Python 3.10+, installs as the `dl-qa` CLI.

It is itself an *agentic* application built on the Anthropic SDK; this repo's code calls Claude. When editing here, keep that distinction in mind: there is a difference between the agent we're building (`src/digital_land_qa_agent/`) and any code we're generating *for* a target repo.

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
- `dl-qa run --target <name> --goal "<goal>"` — full pipeline

## Layout

- [src/digital_land_qa_agent/](src/digital_land_qa_agent/) — package root
  - [__main__.py](src/digital_land_qa_agent/__main__.py) — Click CLI: `dl-qa run / list-targets / profile`
  - [config.py](src/digital_land_qa_agent/config.py) — `Settings` (global) + `TargetConfig` (per-repo) loaders
  - [orchestrator.py](src/digital_land_qa_agent/orchestrator.py) — sequential pipeline + `PipelineResult`
  - [runs.py](src/digital_land_qa_agent/runs.py) — per-run staging dir + JSONL audit log
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

Approval requires **all** of: LLM verdict == `approved`, `ruff check` clean, `python -m py_compile` clean.
`pytest --collect-only` is run for information but does **not** gate approval — the target repo's runtime deps (pyspark, sedona, etc.) are usually not installed in this venv, so the real collect happens when the staged test is moved to the target.

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
