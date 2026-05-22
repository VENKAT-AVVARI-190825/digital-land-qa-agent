"""Tests for the Run/audit-log staging helper."""

from __future__ import annotations

import json

from digital_land_qa_agent.runs import new_run


def test_new_run_creates_unique_dir(tmp_path):
    r1 = new_run(tmp_path, "demo")
    r2 = new_run(tmp_path, "demo")
    assert r1.root != r2.root
    assert r1.root.is_dir() and r2.root.is_dir()


def test_write_staged_test_mirrors_layout(tmp_path):
    run = new_run(tmp_path, "demo")
    written = run.write_staged_test("tests/unit/utils/test_foo.py", "print('hi')\n")
    assert written.read_text() == "print('hi')\n"
    assert written.parent.name == "utils"
    assert written.parent.parent.name == "unit"


def test_audit_log_records_events(tmp_path):
    run = new_run(tmp_path, "demo")
    run.log("custom_event", {"x": 1})
    lines = run.audit_log.read_text().strip().splitlines()
    events = [json.loads(ln)["event"] for ln in lines]
    assert "run_started" in events
    assert "custom_event" in events


def test_write_artifact_dict_serializes_to_json(tmp_path):
    run = new_run(tmp_path, "demo")
    path = run.write_artifact("profile.json", {"k": "v"})
    assert json.loads(path.read_text()) == {"k": "v"}
