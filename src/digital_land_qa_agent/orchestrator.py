"""Sequential pipeline: Profiler -> Planner -> TestWriter -> Critic (with revisions)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from digital_land_qa_agent.agents import (
    CriticAgent,
    PlannerAgent,
    ProfilerAgent,
    TestWriterAgent,
)
from digital_land_qa_agent.config import Settings, TargetConfig
from digital_land_qa_agent.llm import build_client
from digital_land_qa_agent.runs import Run, new_run


@dataclass
class PipelineResult:
    run: Run
    profile: dict[str, Any]
    plan: dict[str, Any]
    staged_path: Path
    verdict: dict[str, Any]
    approved: bool

    def summary(self) -> str:
        v = self.verdict
        status = "APPROVED" if self.approved else "NEEDS REVIEW"
        sc = v["static_checks"]
        lint_summary = ", ".join(
            f"{' '.join(r['command'][:2])}={'ok' if r['ok'] else 'FAIL'}"
            for r in sc.get("lint_per_command", [])
        ) or "no lint commands configured"
        return (
            f"[{status}] {self.plan.get('target_module')} -> {self.staged_path}\n"
            f"  compile_ok={sc['compile_ok']}  lint=({lint_summary})\n"
            f"  pytest_collect_ok={sc['pytest_collect_ok']} (informational)\n"
            f"  notes: {v.get('notes', '')}"
        )


def run_pipeline(
    target: TargetConfig,
    goal: str,
    settings: Settings,
    max_revisions: int = 3,
) -> PipelineResult:
    llm = build_client(settings.model)
    run = new_run(settings.runs_dir, target.name)
    run.log("pipeline_started", {"goal": goal, "llm_mode": llm.mode})

    profiler = ProfilerAgent(llm=llm, run=run)
    planner = PlannerAgent(llm=llm, run=run)
    writer = TestWriterAgent(llm=llm, run=run)
    critic = CriticAgent(llm=llm, run=run)

    profile = profiler.profile(target)
    plan = planner.plan(goal, profile)

    staged_path = writer.write(plan, target)
    verdict = critic.review(staged_path, plan, profile, target=target)

    revisions = 0
    while not verdict["approved"] and revisions < max_revisions:
        revisions += 1
        run.log("revision_started", {"revision": revisions, "issues": verdict.get("issues", [])})
        # In mock mode the writer returns the same fixture; in live mode the
        # critic's issues would be appended to the writer's prompt. We keep
        # this minimal for v1 — the critic's verdict.json is the audit trail.
        staged_path = writer.write(plan, target)
        verdict = critic.review(staged_path, plan, profile, target=target)

    run.log(
        "pipeline_finished",
        {
            "approved": verdict["approved"],
            "revisions": revisions,
            "staged_path": str(staged_path),
        },
    )

    return PipelineResult(
        run=run,
        profile=profile,
        plan=plan,
        staged_path=staged_path,
        verdict=verdict,
        approved=verdict["approved"],
    )
