"""Tests for the runs-aggregation metrics module."""

from __future__ import annotations

from digital_land_qa_agent.metrics import collect
from digital_land_qa_agent.runs import new_run


def _simulate_run(runs_dir, *, approved: bool, revisions: int = 0, in_tokens: int = 100, out_tokens: int = 200) -> None:
    run = new_run(runs_dir, "demo")
    run.log("pipeline_started", {"goal": "Unit tests for foo", "llm_mode": "mock"})
    for _ in range(2):
        run.log("llm_call", {"agent": "x", "mode": "mock", "usage": {"input_tokens": in_tokens, "output_tokens": out_tokens}})
    for i in range(revisions):
        run.log("revision_started", {"revision": i + 1, "issues": []})
    run.log("pipeline_finished", {"approved": approved})


def test_collect_with_no_runs(tmp_path):
    agg = collect(tmp_path / "does-not-exist")
    assert agg.total_runs == 0
    assert agg.per_run == []


def test_collect_aggregates_runs(tmp_path):
    _simulate_run(tmp_path, approved=True, revisions=0)
    _simulate_run(tmp_path, approved=False, revisions=2)
    _simulate_run(tmp_path, approved=True, revisions=1)

    agg = collect(tmp_path)

    assert agg.total_runs == 3
    assert agg.approved == 2
    assert agg.needs_review == 1
    assert agg.incomplete == 0
    assert agg.approval_rate == 2 / 3
    assert agg.avg_revisions == 1.0
    assert agg.total_input_tokens == 600  # 3 runs * 2 calls * 100
    assert agg.total_output_tokens == 1200
    assert agg.mode_counts == {"mock": 3}


def test_collect_handles_incomplete_run(tmp_path):
    run = new_run(tmp_path, "demo")
    run.log("pipeline_started", {"goal": "g", "llm_mode": "mock"})
    # no pipeline_finished event -> incomplete

    agg = collect(tmp_path)
    assert agg.total_runs == 1
    assert agg.incomplete == 1
    assert agg.approved == 0
