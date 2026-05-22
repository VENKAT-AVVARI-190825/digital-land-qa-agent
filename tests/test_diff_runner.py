"""Tests for the diff_runner module."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from digital_land_qa_agent.diff_runner import (
    DiffSummary,
    git_changed_files,
    path_to_module,
    relevant_source_files,
    run_diff,
)


# ---------------------------------------------------------------------------
# Pure helpers — no git, no LLM, no subprocess.
# ---------------------------------------------------------------------------


def test_relevant_source_files_filters_to_src_dirs():
    candidates = [
        Path("src/jobs/utils/flatten_csv.py"),
        Path("src/jobs/utils/__init__.py"),  # skipped
        Path("docs/README.md"),               # skipped (not .py)
        Path("tests/unit/test_x.py"),         # skipped (not under src_dirs)
        Path("src/analytics/foo.py"),
    ]
    src_dirs = ["src/jobs", "src/analytics"]
    result = relevant_source_files(candidates, src_dirs)
    assert result == [
        Path("src/jobs/utils/flatten_csv.py"),
        Path("src/analytics/foo.py"),
    ]


def test_relevant_source_files_no_src_dirs_keeps_any_py():
    candidates = [Path("a.py"), Path("__init__.py"), Path("b.md")]
    assert relevant_source_files(candidates, []) == [Path("a.py")]


def test_path_to_module_strips_src_dir_prefix():
    assert (
        path_to_module(Path("src/jobs/utils/flatten_csv.py"), ["src/jobs", "src/analytics"])
        == "jobs.utils.flatten_csv"
    )


def test_path_to_module_handles_trailing_slash_in_src_dir():
    assert path_to_module(Path("src/jobs/foo.py"), ["src/jobs/"]) == "jobs.foo"


def test_path_to_module_falls_back_when_no_prefix_matches():
    # If a candidate slipped through filtering, don't crash — just return
    # something reasonable so the caller can surface it.
    assert path_to_module(Path("something/odd.py"), ["src/jobs"]) == "something.odd"


# ---------------------------------------------------------------------------
# Git-touching helper — uses a real throwaway repo so we don't mock subprocess.
# ---------------------------------------------------------------------------


def test_git_changed_files_returns_added_and_modified(tmp_path):
    repo = tmp_path / "fake-repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(tmp_path)},
        )

    git("init", "-q", "-b", "main")
    (repo / "a.py").write_text("a = 1\n")
    git("add", "a.py")
    git("commit", "-q", "-m", "first")
    base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    (repo / "b.py").write_text("b = 2\n")  # added
    (repo / "a.py").write_text("a = 99\n")  # modified
    git("add", "a.py", "b.py")
    git("commit", "-q", "-m", "second")

    changed = git_changed_files(repo, base, "HEAD")
    assert sorted(changed) == [Path("a.py"), Path("b.py")]


# ---------------------------------------------------------------------------
# run_diff with explicit files — uses the real pipeline in mock mode.
# ---------------------------------------------------------------------------


def test_run_diff_requires_base_or_files(tmp_path):
    from digital_land_qa_agent.config import Settings, TargetConfig

    target = TargetConfig(name="x", path=tmp_path, src_dirs=["src"])
    settings = Settings()
    with pytest.raises(ValueError):
        run_diff(target=target, settings=settings)


def test_run_diff_caps_at_max_files(tmp_path, monkeypatch):
    from digital_land_qa_agent.config import Settings, TargetConfig

    target = TargetConfig(name="x", path=tmp_path, src_dirs=["src"])
    settings = Settings(runs_dir=tmp_path / "runs")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    files = [Path(f"src/mod_{i}.py") for i in range(20)]
    with pytest.raises(RuntimeError, match="exceeds --max-files"):
        run_diff(target=target, settings=settings, explicit_files=files, max_files=5)


def test_run_diff_skips_non_source(tmp_path, monkeypatch):
    """Passing only non-source files yields an empty summary, not an error."""
    from digital_land_qa_agent.config import Settings, TargetConfig

    target = TargetConfig(name="x", path=tmp_path, src_dirs=["src"])
    settings = Settings(runs_dir=tmp_path / "runs")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    summary = run_diff(
        target=target,
        settings=settings,
        explicit_files=[Path("docs/x.md"), Path("src/__init__.py")],
    )
    assert isinstance(summary, DiffSummary)
    assert summary.files_seen == 2
    assert summary.results == []
