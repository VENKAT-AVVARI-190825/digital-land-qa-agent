"""Tests for the sandboxed filesystem tools."""

from __future__ import annotations

import pytest

from digital_land_qa_agent.runs import new_run
from digital_land_qa_agent.tools import fs


def test_list_and_read_inside_sandbox(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("# a\n")
    (tmp_path / "src" / "b.py").write_text("# b\n")

    files = fs.list_files(tmp_path, "src", "*.py")
    assert files == ["src/a.py", "src/b.py"]

    assert fs.read_file(tmp_path, "src/a.py") == "# a\n"


def test_read_file_rejects_path_escape(tmp_path):
    (tmp_path / "src").mkdir()
    with pytest.raises(fs.SandboxError):
        fs.read_file(tmp_path, "../../etc/passwd")


def test_write_staged_test_lands_under_run_dir(tmp_path):
    run = new_run(tmp_path, "demo")
    written = fs.write_staged_test(run, "tests/unit/test_x.py", "x = 1\n")
    assert str(run.root) in written
    assert "tests/unit/test_x.py" in written
