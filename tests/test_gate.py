"""The pre-registration gate must stay shut unless the plan is approved, recorded and present."""

import pytest

from src.common import gate
from src.common.gate import GateClosedError, gate_open, require_gate


def write_gate(path, approved, commit):
    path.write_text(
        f"analysis_plan_approved: {approved}\nanalysis_plan_commit: {commit}\n", encoding="utf-8"
    )
    return path


def test_closed_gate_blocks(tmp_path):
    g = write_gate(tmp_path / "gate.yaml", "false", "null")
    assert gate_open(g, tmp_path / "plan.md") is False
    with pytest.raises(GateClosedError, match="Refusing to run"):
        require_gate("causal", g, tmp_path / "plan.md")


def test_open_gate_with_commit_and_plan_passes(tmp_path):
    g = write_gate(tmp_path / "gate.yaml", "true", "abc1234")
    plan = tmp_path / "plan.md"
    plan.write_text("# plan", encoding="utf-8")
    require_gate("causal", g, plan)  # no exception


def test_approved_without_commit_is_an_error(tmp_path):
    g = write_gate(tmp_path / "gate.yaml", "true", "null")
    plan = tmp_path / "plan.md"
    plan.write_text("# plan", encoding="utf-8")
    with pytest.raises(GateClosedError, match="analysis_plan_commit is empty"):
        gate_open(g, plan)


def test_approved_without_plan_file_is_an_error(tmp_path):
    g = write_gate(tmp_path / "gate.yaml", "true", "abc1234")
    with pytest.raises(GateClosedError, match="does not exist"):
        gate_open(g, tmp_path / "missing.md")


def test_string_true_does_not_open_gate(tmp_path):
    # A quoted "true" is a string, not a boolean: must not count as approval.
    g = write_gate(tmp_path / "gate.yaml", '"true"', "abc1234")
    assert gate_open(g, tmp_path / "plan.md") is False


def test_repo_gate_is_closed():
    # Until the analysis plan is approved (Phase 4), the committed gate must be shut.
    assert gate_open(gate.GATE_FILE, gate.PLAN_FILE) is False
