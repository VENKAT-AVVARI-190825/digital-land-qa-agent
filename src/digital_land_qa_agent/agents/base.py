"""Base agent: system-prompt loading, single-shot model invocation, JSON parsing.

We deliberately keep the loop simple: each specialist makes one model call
with the relevant tools, parses the text response, and returns structured
output. In mock mode the tools list is unused; in live mode we still drive
tool_use in a small loop inside subclasses that need it (Profiler).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from digital_land_qa_agent.llm import LLMClient
from digital_land_qa_agent.runs import Run

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@dataclass
class BaseAgent:
    name: str
    llm: LLMClient
    run: Run

    @property
    def system_prompt(self) -> str:
        path = PROMPTS_DIR / f"{self.name}.md"
        return path.read_text()

    def call(
        self,
        user_content: str,
        tools: list[dict] | None = None,
        max_tokens: int = 8000,
    ) -> dict[str, Any]:
        resp = self.llm.messages(
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_content}],
            tools=tools,
            max_tokens=max_tokens,
            agent_name=self.name,
        )
        self.run.log(
            "llm_call",
            {
                "agent": self.name,
                "mode": getattr(self.llm, "mode", "unknown"),
                "stop_reason": resp.get("stop_reason"),
                "usage": resp.get("usage"),
            },
        )
        return resp

    @staticmethod
    def extract_text(resp: dict[str, Any]) -> str:
        chunks = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
        return "\n".join(chunks).strip()

    @staticmethod
    def extract_json(resp: dict[str, Any]) -> dict | list:
        text = BaseAgent.extract_text(resp)
        # Tolerate fenced code blocks.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        return json.loads(text)
