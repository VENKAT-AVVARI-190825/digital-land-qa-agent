"""Enumerate changed source files in a target repo and run the pipeline per file.

Powers the ``dl-qa diff`` command and the GitHub Action that fires the agent
on pushes. The trigger sits outside the framework (a workflow), but the
file-enumeration + per-file pipeline orchestration lives here so it's
testable in isolation.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from digital_land_qa_agent.config import Settings, TargetConfig
from digital_land_qa_agent.orchestrator import PipelineResult, run_pipeline


@dataclass
class DiffSummary:
    files_seen: int
    files_skipped: int
    results: list[PipelineResult]

    @property
    def approved(self) -> int:
        return sum(1 for r in self.results if r.approved)

    @property
    def needs_review(self) -> int:
        return sum(1 for r in self.results if not r.approved)


def git_changed_files(target_path: Path, base: str, head: str) -> list[Path]:
    """Return paths changed between ``base`` and ``head`` (added or modified)."""
    proc = subprocess.run(
        [
            "git", "-C", str(target_path),
            "diff", "--name-only", "--diff-filter=AM",
            f"{base}..{head}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in proc.stdout.splitlines() if line.strip()]


def relevant_source_files(candidates: list[Path], src_dirs: list[str]) -> list[Path]:
    """Filter to ``.py`` files under one of ``src_dirs``, skipping __init__.py."""
    if not src_dirs:
        return [p for p in candidates if p.suffix == ".py" and p.name != "__init__.py"]
    cleaned = [d.rstrip("/") + "/" for d in src_dirs]
    keep = []
    for p in candidates:
        if p.suffix != ".py" or p.name == "__init__.py":
            continue
        if any(str(p).startswith(d) for d in cleaned):
            keep.append(p)
    return keep


def path_to_module(path: Path, src_dirs: list[str]) -> str:
    """Turn ``src/jobs/utils/flatten_csv.py`` into ``jobs.utils.flatten_csv``.

    The import root is the *parent* of the matched src_dir. For pyspark-jobs
    src_dirs are ``[src/jobs, src/analytics, src/infra]`` and the import
    root is ``src/`` (which matches the sys.path shim the target's own
    tests use). We strip ``src/`` and convert the remainder to dotted form.
    """
    cleaned = [d.rstrip("/") for d in src_dirs]
    for d in cleaned:
        prefix = d + "/"
        if str(path).startswith(prefix):
            parent = str(Path(d).parent)
            if parent in (".", ""):
                rel = path
            else:
                rel = Path(str(path)[len(parent) + 1 :])
            return ".".join(rel.with_suffix("").parts)
    return ".".join(path.with_suffix("").parts)


def goal_for(module_path: str) -> str:
    return f"Unit tests for {module_path}"


def run_diff(
    target: TargetConfig,
    settings: Settings,
    base: str | None = None,
    head: str = "HEAD",
    explicit_files: list[Path] | None = None,
    max_files: int = 10,
) -> DiffSummary:
    """Run the pipeline for each changed source file.

    Either ``base`` or ``explicit_files`` must be provided. ``explicit_files``
    takes precedence and is the way the consumer workflow passes a known set
    (e.g. when GitHub gives a list of changed files in a push payload).
    """
    if explicit_files is not None:
        candidates = list(explicit_files)
    elif base is not None:
        candidates = git_changed_files(target.path, base, head)
    else:
        raise ValueError("Provide either --base or --files")

    relevant = relevant_source_files(candidates, target.src_dirs)

    if len(relevant) > max_files:
        raise RuntimeError(
            f"Refusing to run: {len(relevant)} changed files exceeds --max-files={max_files}. "
            "Trigger a manual run if this is intentional."
        )

    results: list[PipelineResult] = []
    for src_path in relevant:
        module = path_to_module(src_path, target.src_dirs)
        result = run_pipeline(target, goal_for(module), settings)
        results.append(result)

    return DiffSummary(
        files_seen=len(candidates),
        files_skipped=len(candidates) - len(relevant),
        results=results,
    )
