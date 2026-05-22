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


def test_run_command_returns_127_when_command_missing(tmp_path):
    f = tmp_path / "x"
    f.write_text("")
    result = runners.run_command(["this-command-does-not-exist-xyz", str(f)])
    assert not result.ok
    assert result.returncode == 127


def test_run_lint_commands_substitutes_file_placeholder(tmp_path):
    """{file} in argv gets replaced with the absolute file path."""
    f = tmp_path / "ok.py"
    f.write_text("x = 1\n")
    results = runners.run_lint_commands(
        [["python", "-c", "import sys; print(sys.argv[1])", "{file}"]],
        f,
    )
    assert len(results) == 1
    assert results[0].ok
    assert str(f.resolve()) in results[0].stdout


def test_run_lint_commands_empty_list_returns_empty(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text("x = 1\n")
    assert runners.run_lint_commands([], f) == []
