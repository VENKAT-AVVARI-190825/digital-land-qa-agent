"""Per-run staging directories and audit logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Run:
    root: Path
    target_name: str

    @property
    def staged_tests_dir(self) -> Path:
        return self.root / self.target_name / "tests"

    @property
    def audit_log(self) -> Path:
        return self.root / "audit.jsonl"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    def write_artifact(self, name: str, content: str | dict | list) -> Path:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / name
        if isinstance(content, str):
            path.write_text(content)
        else:
            path.write_text(json.dumps(content, indent=2, default=str))
        self.log("artifact_written", {"name": name, "path": str(path)})
        return path

    def write_staged_test(self, relative_path: str, content: str) -> Path:
        """Write a test file under runs/<ts>/<target>/tests/<relative_path>.

        relative_path is the destination inside the target repo (e.g.
        'unit/utils/test_flatten_csv.py'). We mirror that layout in staging.
        """
        if relative_path.startswith("tests/"):
            relative_path = relative_path[len("tests/") :]
        dest = self.staged_tests_dir / relative_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        self.log("staged_test_written", {"path": str(dest), "bytes": len(content)})
        return dest

    def log(self, event: str, payload: dict[str, Any]) -> None:
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        with self.audit_log.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")


def new_run(runs_dir: Path, target_name: str) -> Run:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    root = runs_dir / ts
    root.mkdir(parents=True, exist_ok=False)
    run = Run(root=root, target_name=target_name)
    run.log("run_started", {"target": target_name, "root": str(root)})
    return run
