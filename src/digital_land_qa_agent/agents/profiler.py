"""ProfilerAgent: produces a RepoProfile describing the target repo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from digital_land_qa_agent.agents.base import BaseAgent
from digital_land_qa_agent.config import TargetConfig


class ProfilerAgent(BaseAgent):
    def __init__(self, llm, run):
        super().__init__(name="profiler", llm=llm, run=run)

    def profile(self, target: TargetConfig) -> dict[str, Any]:
        prompt = self._build_prompt(target)
        resp = self.call(prompt)
        profile = self.extract_json(resp)
        assert isinstance(profile, dict)
        self.run.write_artifact("profile.json", profile)
        return profile

    def _build_prompt(self, target: TargetConfig) -> str:
        # In live mode the Profiler would use list_files/read_file tools; for
        # now we surface a compact view of the repo so a single-shot prompt
        # still works.
        return json.dumps(
            {
                "task": "profile",
                "target": {
                    "name": target.name,
                    "path": str(target.path),
                    "language": target.language,
                    "framework": target.framework,
                    "test_framework": target.test_framework,
                    "src_dirs": target.src_dirs,
                    "test_dir": target.test_dir,
                    "notes": target.notes,
                },
                "top_level": _safe_listdir(target.path),
            },
            indent=2,
        )


def _safe_listdir(path: Path) -> list[str]:
    try:
        return sorted(p.name for p in path.iterdir() if not p.name.startswith("."))
    except FileNotFoundError:
        return []
