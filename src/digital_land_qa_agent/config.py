"""Config loading: global settings + per-target YAML."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


@dataclass
class Settings:
    model: str = "claude-opus-4-7"
    thinking: str = "adaptive"
    effort: str = "xhigh"
    task_budget_tokens: int = 200_000
    max_tokens: int = 64_000
    max_tool_rounds: int = 12
    hitl_required: bool = True
    runs_dir: Path = field(default_factory=lambda: REPO_ROOT / "runs")

    @classmethod
    def load(cls) -> "Settings":
        path = CONFIG_DIR / "settings.yaml"
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
        runs_dir = Path(os.environ.get("DL_QA_RUNS_DIR", REPO_ROOT / "runs")).expanduser()
        return cls(
            model=os.environ.get("DL_QA_MODEL", data.get("model", "claude-opus-4-7")),
            thinking=data.get("thinking", "adaptive"),
            effort=data.get("effort", "xhigh"),
            task_budget_tokens=int(
                os.environ.get("DL_QA_TASK_BUDGET_TOKENS", data.get("task_budget_tokens", 200_000))
            ),
            max_tokens=data.get("max_tokens", 64_000),
            max_tool_rounds=data.get("max_tool_rounds", 12),
            hitl_required=data.get("hitl_required", True),
            runs_dir=runs_dir,
        )


@dataclass
class TargetConfig:
    name: str
    path: Path
    language: str | None = None
    framework: str | None = None
    test_framework: str | None = None
    src_dirs: list[str] = field(default_factory=list)
    test_dir: str | None = None
    data_quality: bool = False
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, name: str) -> "TargetConfig":
        path = CONFIG_DIR / "targets" / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(
                f"No target config at {path}. Copy config/targets/_template.yaml and edit."
            )
        data = yaml.safe_load(path.read_text())
        repo_path = Path(data["path"]).expanduser().resolve()
        return cls(
            name=data["name"],
            path=repo_path,
            language=data.get("language"),
            framework=data.get("framework"),
            test_framework=data.get("test_framework"),
            src_dirs=data.get("src_dirs", []),
            test_dir=data.get("test_dir"),
            data_quality=data.get("data_quality", False),
            notes=data.get("notes", ""),
            extra={k: v for k, v in data.items() if k not in {
                "name", "path", "language", "framework", "test_framework",
                "src_dirs", "test_dir", "data_quality", "notes",
            }},
        )


def list_targets() -> list[str]:
    """Return names of all configured target repos."""
    targets_dir = CONFIG_DIR / "targets"
    return sorted(
        p.stem for p in targets_dir.glob("*.yaml") if not p.stem.startswith("_")
    )
