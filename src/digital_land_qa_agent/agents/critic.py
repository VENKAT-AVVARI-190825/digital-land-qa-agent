"""CriticAgent: static-checks the staged test file and gives a verdict.

Two layers of scrutiny:
1. Local subprocess checks (ruff, pytest --collect-only) — deterministic,
   run regardless of LLM mode.
2. LLM verdict — judges style conformance against the profile. In mock
   mode this returns a canned approval; in live mode the model is asked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from digital_land_qa_agent.agents.base import BaseAgent
from digital_land_qa_agent.tools import runners


class CriticAgent(BaseAgent):
    def __init__(self, llm, run):
        super().__init__(name="critic", llm=llm, run=run)

    def review(
        self,
        staged_path: Path,
        plan: dict[str, Any],
        profile: dict[str, Any],
        target_root: Path | None = None,
    ) -> dict[str, Any]:
        ruff = runners.run_ruff(staged_path)
        compile_ = runners.run_python_compile(staged_path)
        # pytest_collect is informational only — requires the target repo's
        # runtime deps (pyspark, etc.) in this venv, which often aren't here.
        collect = runners.run_pytest_collect(staged_path, target_root=target_root)
        self.run.log(
            "critic_static_checks",
            {
                "ruff": ruff.as_dict(),
                "compile": compile_.as_dict(),
                "pytest_collect": collect.as_dict(),
            },
        )

        prompt = json.dumps(
            {
                "task": "review",
                "plan": plan,
                "profile_style_hints": profile.get("style_hints", {}),
                "staged_file": staged_path.read_text(),
                "ruff": ruff.as_dict(),
                "compile": compile_.as_dict(),
                "pytest_collect": collect.as_dict(),
            },
            indent=2,
        )
        resp = self.call(prompt)
        verdict = self.extract_json(resp)
        assert isinstance(verdict, dict)

        verdict["static_checks"] = {
            "ruff_ok": ruff.ok,
            "compile_ok": compile_.ok,
            "pytest_collect_ok": collect.ok,  # informational
        }
        # Hard gates: ruff + compile. pytest_collect is reported but does not
        # block approval (target repo's env will run it for real).
        verdict["approved"] = (
            verdict.get("verdict") == "approved" and ruff.ok and compile_.ok
        )
        self.run.write_artifact("critic_verdict.json", verdict)
        return verdict
