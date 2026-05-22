"""TestWriterAgent: emit pytest code for a TestPlan and stage it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from digital_land_qa_agent.agents.base import BaseAgent
from digital_land_qa_agent.config import TargetConfig
from digital_land_qa_agent.tools import fs as fs_tools


class TestWriterAgent(BaseAgent):
    def __init__(self, llm, run):
        super().__init__(name="test_writer", llm=llm, run=run)

    def write(self, plan: dict[str, Any], target: TargetConfig) -> Path:
        source = _safe_read(target.path / plan["target_source_path"])
        anchors = {
            p: _safe_read(target.path / p)
            for p in plan.get("style_anchor_paths", [])
        }
        prompt = json.dumps(
            {
                "task": "write_tests",
                "plan": plan,
                "source_code": source,
                "style_anchors": anchors,
            },
            indent=2,
        )
        resp = self.call(prompt, max_tokens=16_000)
        content = self.extract_text(resp)
        # Allow fenced ``` python ... ``` responses too.
        content = _strip_code_fence(content)
        staged_path = fs_tools.write_staged_test(
            self.run, plan["destination_path"], content
        )
        return Path(staged_path)


def _safe_read(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # drop the opening fence (``` or ```python) and the closing fence
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines) + "\n"
    return stripped + "\n"
