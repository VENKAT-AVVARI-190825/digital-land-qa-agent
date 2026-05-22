"""Anthropic tool-use schemas. The orchestrator passes the relevant subset
to each agent depending on what that agent is allowed to do.

We keep schemas explicit (not auto-generated) so it's easy to see what the
model can ask for. Today only Profiler and TestWriter actually need tools
in live mode; mock mode ignores tools entirely.
"""

from __future__ import annotations

LIST_FILES = {
    "name": "list_files",
    "description": "List files under a directory of the target repo (relative to its root). Optional glob pattern.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subdir": {"type": "string", "description": "Path relative to target repo root. Empty for root."},
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '*.py'."},
        },
        "required": [],
    },
}

READ_FILE = {
    "name": "read_file",
    "description": "Read a file from inside the target repo. Path is relative to its root.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relative_path": {"type": "string"},
        },
        "required": ["relative_path"],
    },
}

WRITE_STAGED_TEST = {
    "name": "write_staged_test",
    "description": (
        "Write a generated test file into the run's staging area. "
        "destination_path is the path inside the target repo "
        "(e.g. tests/unit/utils/test_foo.py); we mirror that under runs/."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "destination_path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["destination_path", "content"],
    },
}


PROFILER_TOOLS = [LIST_FILES, READ_FILE]
PLANNER_TOOLS = [LIST_FILES, READ_FILE]
TEST_WRITER_TOOLS = [READ_FILE, WRITE_STAGED_TEST]
CRITIC_TOOLS: list[dict] = []  # Critic uses subprocess runners directly, not LLM tools.
