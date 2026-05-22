"""Deterministic fixtures returned by :class:`MockClient`.

Each entry returns a list of Anthropic-shaped content blocks. We keep these
hand-written rather than recorded so the mock pipeline stays readable and
the demo run is reproducible without any live calls.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Profiler — describes the pyspark-jobs repo it just walked.
# ---------------------------------------------------------------------------

_PROFILE_PYSPARK_JOBS: dict[str, Any] = {
    "target_name": "pyspark-jobs",
    "language": "python",
    "framework": "pyspark",
    "test_framework": "pytest",
    "src_dirs": ["src/jobs", "src/analytics", "src/infra"],
    "test_layout": "tests/{unit,integration,acceptance}",
    "style_hints": {
        "uses_test_classes": True,
        "class_pattern": "Test<Module>",
        "uses_mock_in_units": True,
        "sys_path_shim": True,
        "module_docstring": True,
        "method_docstrings": True,
        "marker_for_unit_tests": "@pytest.mark.unit",
    },
    "markers_used": ["unit", "integration", "acceptance", "slow", "database", "spark"],
    "style_anchor_paths": [
        "tests/unit/utils/test_df_utils.py",
        "tests/unit/utils/test_logger_config.py",
    ],
    "coverage_gaps": [
        "jobs.utils.flatten_csv",
        "jobs.utils.geometry_utils",
        "jobs.utils.s3_utils",
        "jobs.utils.postgres_writer_utils",
        "jobs.utils.spark_session",
        "jobs.transform.column_field_transformer",
        "jobs.transform.entity_transformer",
        "jobs.transform.fact_transformer",
    ],
    "constraints": [
        "pytest.ini requires --strict-markers and --cov-fail-under=80",
        "Use unittest.mock.Mock for unit tests (no live Spark)",
        "Tests must be flake8 + isort clean",
    ],
}

# ---------------------------------------------------------------------------
# Planner — for the demo goal "Unit tests for jobs.utils.flatten_csv".
# ---------------------------------------------------------------------------

_PLAN_FLATTEN_CSV: dict[str, Any] = {
    "target_module": "jobs.utils.flatten_csv",
    "target_source_path": "src/jobs/utils/flatten_csv.py",
    "destination_path": "tests/unit/utils/test_flatten_csv.py",
    "test_level": "unit",
    "style_anchor_paths": ["tests/unit/utils/test_df_utils.py"],
    "test_cases": [
        {
            "function": "flatten_json_column",
            "name": "test_returns_unchanged_when_json_column_missing",
            "intent": "If the DataFrame has no 'json' column, the function returns the input unchanged.",
        },
        {
            "function": "flatten_json_column",
            "name": "test_returns_unchanged_when_no_non_null_json_rows",
            "intent": "If the 'json' column exists but every value is null, return the input unchanged.",
        },
        {
            "function": "flatten_geojson_column",
            "name": "test_returns_unchanged_when_geojson_column_missing",
            "intent": "If the DataFrame has no 'geojson' column, the function returns the input unchanged.",
        },
    ],
}

# ---------------------------------------------------------------------------
# TestWriter — pre-canned pytest file matching the user's existing style.
# ---------------------------------------------------------------------------

_TEST_FILE_FLATTEN_CSV = '''"""Unit tests for flatten_csv module."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

import pytest  # noqa: E402

from jobs.utils.flatten_csv import flatten_geojson_column, flatten_json_column  # noqa: E402


@pytest.mark.unit
class TestFlattenJsonColumn:
    """Test suite for flatten_json_column."""

    def test_returns_unchanged_when_json_column_missing(self):
        """If 'json' is not in columns, the input DataFrame is returned as-is."""
        mock_df = Mock()
        mock_df.columns = ["entity", "name"]

        result = flatten_json_column(mock_df)

        assert result is mock_df
        mock_df.select.assert_not_called()

    @patch("jobs.utils.flatten_csv.col")
    def test_returns_unchanged_when_no_non_null_json_rows(self, _mock_col):
        """If every row's 'json' value is null, return the input DataFrame."""
        mock_df = Mock()
        mock_df.columns = ["entity", "json"]

        filtered = MagicMock()
        filtered.first.return_value = None
        selected = MagicMock()
        selected.filter.return_value = filtered
        mock_df.select.return_value = selected

        result = flatten_json_column(mock_df)

        assert result is mock_df
        mock_df.withColumn.assert_not_called()


@pytest.mark.unit
class TestFlattenGeojsonColumn:
    """Test suite for flatten_geojson_column."""

    def test_returns_unchanged_when_geojson_column_missing(self):
        """If 'geojson' is not in columns, the input DataFrame is returned as-is."""
        mock_df = Mock()
        mock_df.columns = ["entity", "name"]

        result = flatten_geojson_column(mock_df)

        assert result is mock_df
        mock_df.withColumn.assert_not_called()
'''

# ---------------------------------------------------------------------------
# Critic — approves the staged file on first pass for the demo.
# ---------------------------------------------------------------------------

_CRITIC_APPROVED: dict[str, Any] = {
    "verdict": "approved",
    "issues": [],
    "notes": "Style matches anchor (class-based, Mock-based, sys.path shim, docstrings). "
    "Unit marker present. flake8/ruff clean. pytest --collect-only succeeded.",
}


def _text_block(payload: dict | str) -> list[dict[str, Any]]:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    return [{"type": "text", "text": text}]


def get(agent_name: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the mock content blocks for a given agent.

    Today this is keyed only by ``agent_name``. The ``messages`` argument is
    accepted so we can branch on user input later (e.g. different targets,
    different goals) without changing the call site.
    """
    if agent_name == "profiler":
        return _text_block(_PROFILE_PYSPARK_JOBS)
    if agent_name == "planner":
        return _text_block(_PLAN_FLATTEN_CSV)
    if agent_name == "test_writer":
        return _text_block(_TEST_FILE_FLATTEN_CSV)
    if agent_name == "critic":
        return _text_block(_CRITIC_APPROVED)
    raise KeyError(f"No mock fixture registered for agent '{agent_name}'")
