"""CriticAgent: static-checks the staged test file and gives a verdict.

Two layers of scrutiny:
1. Local subprocess checks (compile + the target's configured lint commands +
   pytest collect) — deterministic, run regardless of LLM mode.
2. LLM verdict — judges style conformance against the profile. In mock
   mode this returns a canned approval; in live mode the model is asked.

Approval requires the LLM verdict to be "approved" AND compile to pass AND
every configured lint command to pass. pytest_collect is informational only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from digital_land_qa_agent.agents.base import BaseAgent
from digital_land_qa_agent.config import TargetConfig
from digital_land_qa_agent.tools import runners


class CriticAgent(BaseAgent):
    def __init__(self, llm, run):
        super().__init__(name="critic", llm=llm, run=run)

    def review(
        self,
        staged_path: Path,
        plan: dict[str, Any],
        profile: dict[str, Any],
        target: TargetConfig | None = None,
    ) -> dict[str, Any]:
        target_root = target.path if target else None
        lint_commands = target.lint_commands if target else []

        compile_ = runners.run_python_compile(staged_path)
        lint_results = runners.run_lint_commands(lint_commands, staged_path, cwd=target_root)
        collect = runners.run_pytest_collect(staged_path, target_root=target_root)

        self.run.log(
            "critic_static_checks",
            {
                "compile": compile_.as_dict(),
                "lint": [r.as_dict() for r in lint_results],
                "pytest_collect": collect.as_dict(),
            },
        )

        prompt = json.dumps(
            {
                "task": "review",
                "plan": plan,
                "profile_style_hints": profile.get("style_hints", {}),
                "staged_file": staged_path.read_text(),
                "compile": compile_.as_dict(),
                "lint": [r.as_dict() for r in lint_results],
                "pytest_collect": collect.as_dict(),
            },
            indent=2,
        )
        resp = self.call(prompt)
        verdict = self.extract_json(resp)
        assert isinstance(verdict, dict)

        lint_ok = all(r.ok for r in lint_results) if lint_results else True
        verdict["static_checks"] = {
            "compile_ok": compile_.ok,
            "lint_ok": lint_ok,
            "lint_per_command": [
                {"command": r.command, "ok": r.ok, "returncode": r.returncode}
                for r in lint_results
            ],
            "pytest_collect_ok": collect.ok,  # informational
        }
        # Hard gates: compile + every configured lint command. pytest_collect
        # is reported but does not block (target repo's env runs it for real).
        verdict["approved"] = (
            verdict.get("verdict") == "approved" and compile_.ok and lint_ok
        )
        self.run.write_artifact("critic_verdict.json", verdict)
        return verdict
