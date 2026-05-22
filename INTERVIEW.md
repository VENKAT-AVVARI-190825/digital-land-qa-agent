# Interview reference

Personal reference for mapping this repo to a Technical Lead JD focused on agentic AI / QA automation / digital analytics. Pull up on phone during the call if needed.

## Headline

This repo covers ~80% of the JD's **AI / QA-automation pillar** (agentic AI, test automation, HITL, observability, CI). It does **not** touch the **Google Analytics pillar** — that's a separate competency to handle separately. The PoC is deliberately scoped to prove the agentic-AI loop works against a real client repo (`digital-land/pyspark-jobs`).

---

## Responsibilities → repo

| JD responsibility | Where in the repo |
|---|---|
| Test automation frameworks that increase release quality, reduce manual regression effort | The whole pipeline — [orchestrator.py](src/digital_land_qa_agent/orchestrator.py), agents in [agents/](src/digital_land_qa_agent/agents/) |
| Support continuous integration practices | [.github/workflows/ci.yml](.github/workflows/ci.yml) — ruff + pytest on Python 3.10 / 3.11 / 3.12 |
| AI agents to automate repetitive workflows | The whole demo — dev writes implementation, agent writes the tests |
| Agentic AI patterns that organize tasks into goal-oriented plans | Profiler → Planner → TestWriter → Critic sequential pipeline; structured JSON between stages |
| Autonomous agents with human-in-the-loop oversight | `hitl_required: true` in [config/settings.yaml](config/settings.yaml); agent stages to `runs/`, human moves to target |
| Compliance with enterprise standards, performance expectations and security guardrails | [tools/fs.py](src/digital_land_qa_agent/tools/fs.py) `SandboxError`; Critic gates on target's own lint commands |
| Standardize coding practices, version control, test automation guidelines | ruff on framework, target's own black + flake8 + isort on generated tests, 16 framework tests, clean git history |
| Coordinate integration of AI agents with existing applications and APIs, traceable decision paths | Structured plan / profile / verdict JSON between agents; JSONL audit log per run; `dl-qa metrics` rollup |
| Monitor performance of deployed AI agents, refining over time | [metrics.py](src/digital_land_qa_agent/metrics.py) + `dl-qa metrics` — approval rate, avg revisions, token spend, mode counts |
| Guide root cause analysis for production issues | `runs/<ts>/audit.jsonl` records every model call, every tool call, every artifact — *which* agent failed is always answerable |
| Prepare technical documentation and knowledge share | [README.md](README.md), [CLAUDE.md](CLAUDE.md), per-agent system prompts in [prompts/](src/digital_land_qa_agent/prompts/) |
| Ethical AI, data privacy, secure coding | Agent never writes to target repo (staging-only); sandboxed tool surface; no creds in code (`.env.example` only); audit-by-default |

## Qualifications → repo

| JD qualification | Repo evidence |
|---|---|
| Test automation, maintainable test suites | Generated tests match target's existing style; framework has its own pytest suite (16 tests, green) |
| AI agents: prompt orchestration, context management, evaluation of outputs | Four narrow system prompts in [prompts/](src/digital_land_qa_agent/prompts/); Critic agent does evaluation |
| Agentic AI: task decomposition, planning, tool use | Planner decomposes goal → test cases; tool registry in [tools/registry.py](src/digital_land_qa_agent/tools/registry.py); sandboxed tool execution |
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
> The human-in-the-loop boundary is enforced architecturally — the agent literally cannot write into the target repo. Generated tests stage in this framework's `runs/` directory; a human moves them across.
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

# 4. Show the staged output + audit log side-by-side in IDE
ls runs/<ts>/

# 5. Show observability across runs
dl-qa metrics
```

The most persuasive single visual: open the staged test file alongside the `audit.jsonl` in the IDE so the auditor can see every decision the system made.
