"""LLM client wrapper. Routes to live Anthropic API or deterministic mock."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


class LLMClient(Protocol):
    """Minimal interface every agent uses to talk to a model.

    Agents do not run their own tool-use loops; the orchestrator handles that
    via :meth:`messages`. Mock and live clients implement the same shape so
    swapping is transparent.
    """

    mode: str  # "live" or "mock"

    def messages(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8000,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        """Return an Anthropic-shaped response dict.

        Expected keys: ``content`` (list of blocks), ``stop_reason``,
        ``usage`` (input_tokens, output_tokens).
        """
        ...


@dataclass
class LiveClient:
    """Anthropic SDK wrapper. Only imported if ANTHROPIC_API_KEY is set."""

    model: str
    mode: str = "live"

    def __post_init__(self) -> None:
        from anthropic import Anthropic  # imported lazily

        self._sdk = Anthropic()

    def messages(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 8000,
        agent_name: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        resp = self._sdk.messages.create(**kwargs)
        return {
            "content": [block.model_dump() for block in resp.content],
            "stop_reason": resp.stop_reason,
            "usage": {
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        }


def build_client(model: str) -> LLMClient:
    """Pick the right client based on ANTHROPIC_API_KEY presence."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return LiveClient(model=model)
    from digital_land_qa_agent.llm.mock import MockClient

    return MockClient()
