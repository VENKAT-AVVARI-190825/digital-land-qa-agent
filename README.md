# digital-land-qa-agent

Multi-agent QA automation framework for [digital-land](https://github.com/digital-land) Python repos. Reads a target repo, generates pytest tests, and stages them for human review.

> **Status:** Proof of concept demonstrating agentic AI patterns for QA automation. Not production-ready.

---

## What it does

Given a goal and a target repo, four specialist agents collaborate to produce a pytest file that matches the target repo's existing test style:

```
ProfilerAgent    →    PlannerAgent    →    TestWriterAgent    →    CriticAgent
   scans repo,       picks function,       writes pytest          static checks
   detects style     drafts cases          matching style         + LLM review

                                                                  loops back to
                                                                  TestWriter if
                                                                  not approved
```

The Critic gates output on `ruff` and Python compile checks before anything reaches a human. Approved tests land under `runs/<timestamp>/<target>/...` for review; a human moves them into the target repo. **The agent never writes into the target repo directly.**

## Quick start

```bash
make dev                              # editable install with dev extras
dl-qa list-targets                    # show configured targets
dl-qa run \
  --target pyspark-jobs \
  --goal "Unit tests for jobs.utils.flatten_csv"
dl-qa metrics                         # aggregate stats across all runs
```

Without `ANTHROPIC_API_KEY` set, the framework runs in **mock mode** — deterministic stubs return canned responses so you can exercise the full pipeline without burning tokens. Set `ANTHROPIC_API_KEY` to switch to live Claude calls.

## Architecture

| Layer | Module | Responsibility |
|---|---|---|
| CLI | [`__main__.py`](src/digital_land_qa_agent/__main__.py) | `dl-qa run / list-targets / profile / metrics` |
| Orchestration | [`orchestrator.py`](src/digital_land_qa_agent/orchestrator.py) | Sequential pipeline, HITL gate, revision loop |
| Agents | [`agents/`](src/digital_land_qa_agent/agents/) | Profiler, Planner, TestWriter, Critic |
| LLM | [`llm/`](src/digital_land_qa_agent/llm/) | Anthropic SDK wrapper + deterministic mock |
| Tools | [`tools/`](src/digital_land_qa_agent/tools/) | Sandboxed FS + subprocess runners (ruff, py_compile) |
| Prompts | [`prompts/`](src/digital_land_qa_agent/prompts/) | One Markdown system prompt per agent |
| Observability | [`runs.py`](src/digital_land_qa_agent/runs.py), [`metrics.py`](src/digital_land_qa_agent/metrics.py) | Per-run JSONL audit + cross-run rollup |
| Config | [`config.py`](src/digital_land_qa_agent/config.py), [`config/`](config/) | Global settings + per-target YAML |

## Design principles

- **Separation of concerns between agents.** Each agent has a narrow role and its own system prompt. When the pipeline produces a bad output, the audit log makes it obvious *which* agent failed.
- **Human-in-the-loop by default.** `hitl_required: true` in [`config/settings.yaml`](config/settings.yaml). The agent stages, the human decides.
- **Sandboxed tool surface.** [`tools/fs.py`](src/digital_land_qa_agent/tools/fs.py) raises `SandboxError` on any path escape. No tool can write outside the per-run staging directory.
- **Deterministic fallback.** Mock mode means the framework's own CI doesn't depend on a live API and the demo is reproducible.
- **Traceable decisions.** Every model call, every tool call, every artifact is recorded in `runs/<ts>/audit.jsonl`.
- **Bounded autonomy.** Token budgets (`task_budget_tokens`), per-response ceilings (`max_tokens`), and tool-round caps (`max_tool_rounds`) all live in settings.

## Configuring a new target

Copy [`config/targets/_template.yaml`](config/targets/_template.yaml) to `<name>.yaml`, point `path` at a local clone, and run:

```bash
dl-qa run --target <name> --goal "..."
```

## Limitations (PoC scope)

- **Revision loop doesn't yet pass Critic feedback into the Writer's prompt.** The loop runs but in v1 the Writer regenerates without specific issue context. Closing this is the obvious next step before live mode against an unfamiliar target.
- **Profiler uses a static snapshot.** The live Anthropic tool-use loop (so Profiler can call `list_files`/`read_file` on demand) is wired but not yet driven by the Profiler agent.
- **Unit tests only.** Integration and acceptance test generation are next in scope.
- **Single-process.** No queueing, no concurrency. One pipeline at a time.

## Repository layout

```
src/digital_land_qa_agent/
├── __main__.py          # CLI entrypoint
├── orchestrator.py      # Pipeline runner
├── runs.py              # Per-run dir + audit log
├── metrics.py           # Cross-run aggregation
├── config.py            # Settings + target config loaders
├── agents/              # Profiler, Planner, TestWriter, Critic
├── llm/                 # Live + mock clients, fixtures
├── tools/               # Sandboxed FS + subprocess runners
└── prompts/             # System prompt per agent (Markdown)

config/
├── settings.yaml        # Global agent settings
└── targets/             # One YAML per target repo

tests/                   # Framework unit + integration tests
runs/                    # Per-run staging + audit (gitignored)
```

## License

MIT.
