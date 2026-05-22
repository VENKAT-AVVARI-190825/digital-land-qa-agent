"""Aggregate observability over historical runs.

Reads every ``runs/<ts>/audit.jsonl`` and rolls it up into a summary the
operator can use to judge whether the pipeline is improving over time
(approval rate, revisions needed per run, token spend).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunStats:
    run_id: str
    approved: bool | None = None
    revisions: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_mode: str | None = None
    goal: str | None = None


@dataclass
class Aggregate:
    total_runs: int = 0
    approved: int = 0
    needs_review: int = 0
    incomplete: int = 0
    avg_revisions: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    mode_counts: dict[str, int] = field(default_factory=dict)
    per_run: list[RunStats] = field(default_factory=list)

    @property
    def approval_rate(self) -> float:
        finished = self.approved + self.needs_review
        return self.approved / finished if finished else 0.0


def collect(runs_dir: Path) -> Aggregate:
    """Walk ``runs_dir`` and produce an Aggregate over every completed run."""
    agg = Aggregate()
    if not runs_dir.exists():
        return agg

    for run_root in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        audit = run_root / "audit.jsonl"
        if not audit.exists():
            continue
        stats = _stats_for_run(run_root.name, audit)
        agg.per_run.append(stats)
        agg.total_runs += 1
        agg.total_input_tokens += stats.input_tokens
        agg.total_output_tokens += stats.output_tokens
        if stats.llm_mode:
            agg.mode_counts[stats.llm_mode] = agg.mode_counts.get(stats.llm_mode, 0) + 1
        if stats.approved is True:
            agg.approved += 1
        elif stats.approved is False:
            agg.needs_review += 1
        else:
            agg.incomplete += 1

    if agg.per_run:
        agg.avg_revisions = sum(r.revisions for r in agg.per_run) / len(agg.per_run)
    return agg


def _stats_for_run(run_id: str, audit_path: Path) -> RunStats:
    stats = RunStats(run_id=run_id)
    for line in audit_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("event")
        if kind == "pipeline_started":
            stats.goal = event.get("goal")
            stats.llm_mode = event.get("llm_mode")
        elif kind == "llm_call":
            stats.llm_calls += 1
            usage = event.get("usage") or {}
            stats.input_tokens += int(usage.get("input_tokens") or 0)
            stats.output_tokens += int(usage.get("output_tokens") or 0)
            if not stats.llm_mode:
                stats.llm_mode = event.get("mode")
        elif kind == "revision_started":
            stats.revisions += 1
        elif kind == "pipeline_finished":
            stats.approved = bool(event.get("approved"))
    return stats
