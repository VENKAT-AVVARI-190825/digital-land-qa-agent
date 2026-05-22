"""Filesystem tools for agents. Reads are target-scoped; writes are run-scoped."""

from __future__ import annotations

from pathlib import Path

from digital_land_qa_agent.runs import Run


class SandboxError(RuntimeError):
    """Raised when a tool call tries to escape its sandbox."""


def _under(root: Path, candidate: Path) -> Path:
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if root.resolve() not in resolved.parents and resolved != root.resolve():
        raise SandboxError(f"Path {resolved} is outside sandbox {root}")
    return resolved


def list_files(target_root: Path, subdir: str = "", pattern: str = "*") -> list[str]:
    """List files under ``target_root/subdir`` matching ``pattern``. Read-only."""
    base = _under(target_root, Path(subdir)) if subdir else target_root.resolve()
    return sorted(str(p.relative_to(target_root.resolve())) for p in base.rglob(pattern) if p.is_file())


def read_file(target_root: Path, relative_path: str, max_bytes: int = 100_000) -> str:
    """Read a file from inside the target repo."""
    path = _under(target_root, Path(relative_path))
    data = path.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def write_staged_test(run: Run, destination_path: str, content: str) -> str:
    """Write a generated test under the run's staging directory.

    ``destination_path`` is where the file would land in the target repo
    (e.g. ``tests/unit/utils/test_flatten_csv.py``). We mirror that layout
    under ``runs/<ts>/<target>/tests/...``.
    """
    written = run.write_staged_test(destination_path, content)
    return str(written)
