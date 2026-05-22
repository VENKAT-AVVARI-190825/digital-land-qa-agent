"""End-to-end pipeline test in mock mode against the configured pyspark-jobs target."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from digital_land_qa_agent.config import Settings, TargetConfig
from digital_land_qa_agent.orchestrator import run_pipeline


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_pipeline_runs_end_to_end_in_mock_mode(tmp_path, mock_mode, monkeypatch):
    if not Path(os.path.expanduser("~/repos/pyspark-jobs")).exists():
        pytest.skip("pyspark-jobs target repo not cloned at ~/repos/pyspark-jobs")

    monkeypatch.setenv("DL_QA_RUNS_DIR", str(tmp_path))
    settings = Settings.load()
    target = TargetConfig.load("pyspark-jobs")

    result = run_pipeline(
        target,
        goal="Unit tests for jobs.utils.flatten_csv",
        settings=settings,
        max_revisions=1,
    )

    assert result.approved, result.summary()
    assert result.staged_path.exists()
    assert "def test_" in result.staged_path.read_text()
    assert (result.run.artifacts_dir / "profile.json").exists()
    assert (result.run.artifacts_dir / "plan.json").exists()
    assert (result.run.artifacts_dir / "critic_verdict.json").exists()
