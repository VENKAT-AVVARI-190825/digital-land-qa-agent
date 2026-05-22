"""Tests for the subprocess-based critic runners."""

from __future__ import annotations

from digital_land_qa_agent.tools import runners


def test_python_compile_passes_on_valid_file(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text("x = 1\n")
    result = runners.run_python_compile(f)
    assert result.ok
    assert result.returncode == 0


def test_python_compile_fails_on_syntax_error(tmp_path):
    f = tmp_path / "bad.py"
    f.write_text("def broken(:\n")
    result = runners.run_python_compile(f)
    assert not result.ok


def test_ruff_passes_on_clean_file(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text('"""Doc."""\n\nX = 1\n')
    result = runners.run_ruff(f)
    assert result.ok, result.stdout + result.stderr
