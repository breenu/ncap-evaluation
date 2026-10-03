"""Pre-registration gate: no post-2019 treatment-effect estimate runs before the analysis plan is registered (DECISIONS DEC-012).

Any code that estimates post-2019 NCAP treatment effects must call
`require_gate()` before touching the data. The gate opens only when
config/gate.yaml says the analysis plan is approved AND names the commit
that added the approved plan, and docs/analysis_plan.md exists.
"""

from pathlib import Path

from src.common.paths import CONFIG, DOCS, load_yaml

GATE_FILE = CONFIG / "gate.yaml"
PLAN_FILE = DOCS / "analysis_plan.md"


class GateClosedError(RuntimeError):
    """Raised when post-2019 effect estimation is attempted before the plan is approved."""


def gate_open(gate_file: Path = GATE_FILE, plan_file: Path = PLAN_FILE) -> bool:
    cfg = load_yaml(gate_file)
    if cfg.get("analysis_plan_approved") is not True:
        return False
    # An "approved" flag without a recorded plan is a config error, not an open gate.
    if not cfg.get("analysis_plan_commit"):
        raise GateClosedError(
            f"{gate_file.name}: analysis_plan_approved is true but analysis_plan_commit is empty"
        )
    if not plan_file.exists():
        raise GateClosedError(f"{gate_file.name} is open but {plan_file} does not exist")
    return True


def require_gate(what: str, gate_file: Path = GATE_FILE, plan_file: Path = PLAN_FILE) -> None:
    """Stop with a clear message unless the pre-registration gate is open."""
    if not gate_open(gate_file, plan_file):
        raise GateClosedError(
            f"Refusing to run '{what}': it estimates post-2019 treatment effects and "
            "docs/analysis_plan.md has not been approved and committed (config/gate.yaml)."
        )
