# Interview reference

Personal reference for mapping this repo to a Technical Lead JD focused on agentic AI / QA automation / digital analytics. Pull up on phone during the call if needed.

## Headline

This repo covers ~80% of the JD's **AI / QA-automation pillar** (agentic AI, test automation, HITL, observability, CI). It does **not** touch the **Google Analytics pillar** — that's a separate competency to handle separately. The PoC is deliberately scoped to prove the agentic-AI loop works against a real client repo (`digital-land/pyspark-jobs`).

## Live evidence (open if interviewer asks "does it actually work?")

- **Agent repo:** https://github.com/VENKAT-AVVARI-190825/digital-land-qa-agent (public, CI green)
- **Target repo mirror:** https://github.com/VENKAT-AVVARI-190825/pyspark-jobs (private, only the `qa-agent` workflow installed)
- **Auto-opened PR:** https://github.com/VENKAT-AVVARI-190825/pyspark-jobs/pull/2 — triggered by pushing a docstring change to `dev`. Workflow finished in 26 seconds. PR diff contains only the agent-generated test file; `github-actions` is the author; the reviewer checklist is in the PR body. Labels `qa-agent`, `tests`. The developer made no test edits — the agent did.

---

## Responsibilities → repo

| JD responsibility | Where in the repo |
|---|---|
| Test automation frameworks that increase release quality, reduce manual regression effort | The whole pipeline — [orchestrator.py](digital_land_qa_agent/orchestrator.py), agents in [agents/](digital_land_qa_agent/agents/) |
| Support continuous integration practices | [.github/workflows/ci.yml](.github/workflows/ci.yml) — ruff + pytest on Python 3.10 / 3.11 / 3.12 |
| AI agents to automate repetitive workflows | The whole demo — dev writes implementation, agent writes the tests |
| Agentic AI patterns that organize tasks into goal-oriented plans | Profiler → Planner → TestWriter → Critic sequential pipeline; structured JSON between stages |
| Autonomous agents with human-in-the-loop oversight | `hitl_required: true` in [config/settings.yaml](config/settings.yaml); agent stages to `runs/`, human moves to target |
| Compliance with enterprise standards, performance expectations and security guardrails | [tools/fs.py](digital_land_qa_agent/tools/fs.py) `SandboxError`; Critic gates on target's own lint commands |
| Standardize coding practices, version control, test automation guidelines | ruff on framework, target's own black + flake8 + isort on generated tests, 16 framework tests, clean git history |
| Coordinate integration of AI agents with existing applications and APIs, traceable decision paths | Structured plan / profile / verdict JSON between agents; JSONL audit log per run; `dl-qa metrics` rollup |
| Monitor performance of deployed AI agents, refining over time | [metrics.py](digital_land_qa_agent/metrics.py) + `dl-qa metrics` — approval rate, avg revisions, token spend, mode counts |
| Guide root cause analysis for production issues | `runs/<ts>/audit.jsonl` records every model call, every tool call, every artifact — *which* agent failed is always answerable |
| Prepare technical documentation and knowledge share | [README.md](README.md), [CLAUDE.md](CLAUDE.md), per-agent system prompts in [prompts/](digital_land_qa_agent/prompts/) |
| Ethical AI, data privacy, secure coding | Agent never writes to target repo (staging-only); sandboxed tool surface; no creds in code (`.env.example` only); audit-by-default |

## Qualifications → repo

| JD qualification | Repo evidence |
|---|---|
| Test automation, maintainable test suites | Generated tests match target's existing style; framework has its own pytest suite (16 tests, green) |
| AI agents: prompt orchestration, context management, evaluation of outputs | Four narrow system prompts in [prompts/](digital_land_qa_agent/prompts/); Critic agent does evaluation |
| Agentic AI: task decomposition, planning, tool use | Planner decomposes goal → test cases; tool registry in [tools/registry.py](digital_land_qa_agent/tools/registry.py); sandboxed tool execution |
| Scripting / programming for automation | Python 3.10+, Click CLI, type hints, dataclasses |
| Cloud / DevOps practices, CI pipelines, automated quality gates | GitHub Actions matrix CI; Critic is itself a quality gate that mirrors the target's CI rules |
| Communicate complex tech topics clearly | README structure, CLAUDE.md "design principles" section, agent prompts written as docs |

## Not covered (acknowledge openly)

| JD item | What to say |
|---|---|
| Advanced hands-on **Google Analytics** experience | *"That's the analytics pillar of this role; I treat it as adjacent to but separate from the AI / QA work this PoC demonstrates. Happy to walk through GA experience independently."* |
| **10-14 years experience** | CV / interview-conversation item, not a repo item. |
| **Web / mobile** test automation specifically | The framework targets Python repos in v1. Architecture (Profiler / Planner / Writer / Critic) generalises to any test stack — `lint_commands` and the prompt files are the only parts that change for a JS / TS target. |

---

## 90-second pitch (memorise this)

> "The JD asks for someone who can design agentic AI systems, run them safely inside enterprise guardrails, and observe them in production. This PoC shows all three.
>
> The four-agent pipeline does task decomposition and planning — Profiler reads the target repo, Planner picks the function and test cases, TestWriter generates the pytest code matching the target's style, Critic gates the output.
>
> The Critic is config-driven — it runs the *target's* own linters, not mine, so generated tests pass the target's CI by construction. For pyspark-jobs that's black + flake8 + isort; a different target would declare ruff or eslint.
>
> Every model call and tool call lands in an audit log, and `dl-qa metrics` rolls them up — approval rate, average revisions, token spend — so I can tell whether prompt or model changes are actually improving the system.
>
> The human-in-the-loop boundary is enforced architecturally — the agent literally cannot write into the target repo. Generated tests stage in this framework's `runs/` directory, and the GitHub Action opens a pull request via `peter-evans/create-pull-request` so the agent never gets commit access to the target. I have a live PR open right now where a docstring push to `dev` triggered the agent and produced a clean tests-only PR in 26 seconds.
>
> I've kept the Google Analytics pillar separate; that's a different conversation."

## Likely questions & short honest answers

| Question | Answer |
|---|---|
| *Cost per test file?* | Mock mode is free; live mode is one Anthropic call per agent stage. Budget capped at 200k tokens per run via `task_budget_tokens`. |
| *Hallucinations?* | Critic catches syntactic + style hallucinations (target's own linters + py_compile). Semantic hallucinations are why HITL exists — a human always reviews before code lands in the target. |
| *Why four agents instead of one?* | Smaller prompts, clearer failure attribution, easier to swap models per role later (cheaper Haiku for Profiler, Opus for TestWriter). |
| *Why Claude specifically?* | Framework's LLM interface is a `Protocol` — swapping providers is one file. Claude was chosen for Opus 4.7's reasoning quality on tool-use loops. |
| *Private code / PII?* | Today: source is sent to the API. For sensitive clients I'd add a Bedrock or on-prem deployment path — same Anthropic SDK shape, different endpoint. |
| *What's next if you had two weeks?* | (1) Wire Critic feedback into Writer revisions. (2) Run Profiler with real tool-use loop. (3) Add integration-test generation (currently unit-only). (4) Second target to prove generalisation. |
| *How do I know it works?* | `make test` runs 16 framework tests; `dl-qa run --target pyspark-jobs ...` produces an APPROVED test file with all 3 of pyspark-jobs's linters green; that file passes when dropped into pyspark-jobs's real env. |
| *What if Anthropic is down?* | Mock mode returns deterministic fixtures. Framework's own CI doesn't depend on a live API. For production we'd add retry + circuit-breaker around the LLM client. |

## Demo flow (if asked to show it live)

```bash
# 1. Show the configured targets
dl-qa list-targets

# 2. Show the per-target lint config that drives the Critic
cat config/targets/pyspark-jobs.yaml

# 3. Run the full pipeline (mock mode, no API key needed)
dl-qa run --target pyspark-jobs --goal "Unit tests for jobs.utils.flatten_csv"

# 4. Run against an explicit changed file (what the GitHub Action does per push)
dl-qa diff --target pyspark-jobs --files src/jobs/utils/flatten_csv.py

# 5. Show the staged output + audit log side-by-side in IDE
ls runs/<ts>/

# 6. Show observability across runs
dl-qa metrics

# 7. (If asked) show how a target repo would trigger this on every push
cat examples/pyspark-jobs-qa-agent.yml
cat action.yml
```

The most persuasive single visual: open the staged test file alongside the `audit.jsonl` in the IDE so the auditor can see every decision the system made.

## Common follow-up: "How do you trigger this from a developer push?"

Three pieces — see [README.md](README.md#use-as-a-github-action) for full detail:

1. **`dl-qa diff`** enumerates changed files between two git refs, runs the pipeline per file, caps at `--max-files` for cost control.
2. **[action.yml](action.yml)** packages the framework as a composite GitHub Action — any target repo can `uses:` it.
3. **[examples/pyspark-jobs-qa-agent.yml](examples/pyspark-jobs-qa-agent.yml)** is the consumer workflow pyspark-jobs would drop into `.github/workflows/`. On push to `dev`, it runs the action and opens a PR (via `peter-evans/create-pull-request` scoped to `add-paths: tests/**` so only generated test files end up in the diff) — draft if any file needs review. **Agent never commits to the target directly.**

That preserves the HITL guarantee at the infrastructure level: even if the agent mis-generates, the worst case is a noisy PR — never a polluted main branch.

**Working example:** https://github.com/VENKAT-AVVARI-190825/pyspark-jobs/pull/2 — the PR that the docstring push to `dev` produced. 28-second run, clean diff (only `tests/unit/utils/test_flatten_csv.py`), Critic verdict `needs-review=false`.
