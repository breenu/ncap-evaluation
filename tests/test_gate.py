"""The pre-registration gate must stay shut unless the plan is approved, recorded and present."""

import re
import shutil
import subprocess

import pytest

from src.common import gate
from src.common.gate import GateClosedError, gate_open, require_gate
from src.common.paths import ROOT, load_yaml


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


def test_repo_gate_is_closed_or_cites_a_committed_plan():
    """The committed gate is either shut, or open and naming the full hash of a commit that holds the
    analysis plan (DEC-012). Shallow clones (CI) may lack that commit; then only the hash format is checked."""
    cfg = load_yaml(gate.GATE_FILE)
    if cfg.get("analysis_plan_approved") is not True:
        assert gate_open(gate.GATE_FILE, gate.PLAN_FILE) is False
        return
    commit = str(cfg.get("analysis_plan_commit"))
    assert re.fullmatch(r"[0-9a-f]{40}", commit), (
        "analysis_plan_commit must be a full 40-character hash"
    )
    assert gate_open(gate.GATE_FILE, gate.PLAN_FILE) is True
    if shutil.which("git") is None:
        pytest.skip("git not available")
    run = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)  # noqa: E731
    if (
        run("cat-file", "-e", commit).returncode != 0
        and run("rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    ):
        pytest.skip("shallow clone: the plan commit is not in the local history")
    assert run("cat-file", "-e", f"{commit}:docs/analysis_plan.md").returncode == 0, (
        "gate cites a commit without the plan"
    )
