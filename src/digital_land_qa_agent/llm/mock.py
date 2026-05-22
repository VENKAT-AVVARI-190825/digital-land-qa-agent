"""Deterministic mock LLM client.

Returns canned responses keyed by ``agent_name`` so we can exercise the
full orchestrator pipeline without an API key. The mock responses live in
:mod:`digital_land_qa_agent.llm.fixtures` so they're easy to extend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from digital_land_qa_agent.llm import fixtures


@dataclass
class MockClient:
    mode: str = "mock"

    def messages(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8000,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        if agent_name is None:
            raise ValueError("MockClient requires agent_name to look up fixtures")
        fixture = fixtures.get(agent_name, messages)
        return {
            "content": fixture,
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
