"""Subprocess runners used by the Critic agent."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunnerResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "returncode": self.returncode,
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
        }


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> RunnerResult:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as e:
        return RunnerResult(ok=False, returncode=127, stdout="", stderr=str(e))
    except subprocess.TimeoutExpired as e:
        return RunnerResult(ok=False, returncode=124, stdout="", stderr=f"timeout: {e}")
    return RunnerResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def run_ruff(file_path: Path) -> RunnerResult:
    """Lint a single file with ruff. Returns ok=True if clean."""
    return _run(["ruff", "check", str(file_path)])


def run_python_compile(file_path: Path) -> RunnerResult:
    """Byte-compile the file. Catches syntax errors without importing anything.

    This is the hard gate: a file that doesn't parse can never run in the
    target repo's env either.
    """
    return _run(["python", "-m", "py_compile", str(file_path)])


def run_pytest_collect(file_path: Path, target_root: Path | None = None) -> RunnerResult:
    """Run ``pytest --collect-only`` against the target repo's src tree.

    Informational: typically requires the target's runtime deps (pyspark,
    sedona, etc.) installed in this venv, which they often aren't. Surfaces
    in the audit log but does not gate approval.
    """
    import os

    env = os.environ.copy()
    if target_root:
        src = target_root / "src"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else str(src)
    try:
        proc = subprocess.run(
            [
                "python", "-m", "pytest",
                "--collect-only", "-q",
                "--confcutdir", str(file_path.parent),
                str(file_path),
            ],
            cwd=str(target_root) if target_root else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as e:
        return RunnerResult(ok=False, returncode=127, stdout="", stderr=str(e))
    return RunnerResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
