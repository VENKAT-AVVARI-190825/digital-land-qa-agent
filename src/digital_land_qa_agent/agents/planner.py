"""PlannerAgent: turn a free-text goal into a structured TestPlan."""

from __future__ import annotations

import json
from typing import Any

from digital_land_qa_agent.agents.base import BaseAgent


class PlannerAgent(BaseAgent):
    def __init__(self, llm, run):
        super().__init__(name="planner", llm=llm, run=run)

    def plan(self, goal: str, profile: dict[str, Any]) -> dict[str, Any]:
        prompt = json.dumps({"task": "plan", "goal": goal, "profile": profile}, indent=2)
        resp = self.call(prompt)
        plan = self.extract_json(resp)
        assert isinstance(plan, dict)
        self.run.write_artifact("plan.json", plan)
        return plan
