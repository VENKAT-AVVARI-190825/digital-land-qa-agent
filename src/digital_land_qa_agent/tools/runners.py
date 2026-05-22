"""Subprocess runners used by the Critic agent.

The Critic gates on three layers, in order of cost:

1. ``run_python_compile`` — byte-compiles the file. Catches syntax errors.
2. ``run_lint_commands``  — runs whatever lint commands the target repo
   declares (e.g. black + flake8 + isort for pyspark-jobs, ruff for a
   different target). All must exit 0 for approval.
3. ``run_pytest_collect`` — informational; collects against the target's
   src tree but requires the target's runtime deps and so often fails in
   this venv. Surfaces in the audit log but does not gate approval.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunnerResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    command: list[str] | None = None

    def as_dict(self) -> dict:
        return {
            "command": self.command,
            "ok": self.ok,
            "returncode": self.returncode,
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
        }


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 60,
) -> RunnerResult:
    """Run an arbitrary subprocess and capture output."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        return RunnerResult(ok=False, returncode=127, stdout="", stderr=str(e), command=cmd)
    except subprocess.TimeoutExpired as e:
        return RunnerResult(ok=False, returncode=124, stdout="", stderr=f"timeout: {e}", command=cmd)
    return RunnerResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        command=cmd,
    )


def run_python_compile(file_path: Path) -> RunnerResult:
    """Byte-compile the file. Hard gate: a file that won't parse can't run."""
    return run_command(["python", "-m", "py_compile", str(file_path)])


def run_lint_commands(
    commands: list[list[str]],
    file_path: Path,
    cwd: Path | None = None,
) -> list[RunnerResult]:
    """Run each configured lint command against ``file_path``.

    ``{file}`` placeholders in any argv slot are replaced with the absolute
    path of ``file_path``. ``cwd`` should typically be the target repo root
    so the linter picks up the target's config files (.flake8, .isort.cfg,
    pyproject.toml).
    """
    results = []
    abs_path = str(file_path.resolve())
    for raw in commands:
        cmd = [abs_path if arg == "{file}" else arg.replace("{file}", abs_path) for arg in raw]
        results.append(run_command(cmd, cwd=cwd))
    return results


def run_pytest_collect(file_path: Path, target_root: Path | None = None) -> RunnerResult:
    """Run ``pytest --collect-only`` against the target repo's src tree.

    Informational: typically requires the target's runtime deps (pyspark,
    sedona, etc.) in this venv, which often aren't here.
    """
    env = os.environ.copy()
    if target_root:
        src = target_root / "src"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else str(src)
    return run_command(
        [
            "python", "-m", "pytest",
            "--collect-only", "-q",
            "--confcutdir", str(file_path.parent),
            str(file_path),
        ],
        cwd=target_root,
        env=env,
    )
