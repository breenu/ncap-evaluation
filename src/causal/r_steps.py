"""Gated launchers for the Layer A R steps (hard rule 4).

    python -m src.causal.r_steps cs        Callaway & Sant'Anna (src/causal/cs_did.R; DEC-144)
    python -m src.causal.r_steps honest    HonestDiD on the primary event study (src/causal/honest.R; DEC-143)
"""

import os
import subprocess
import sys

from src.common.gate import require_gate

ENV = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}


def main(argv: list[str]) -> None:
    step = argv[0] if argv else ""
    if step == "cs":
        require_gate("Callaway & Sant'Anna")
        subprocess.run(["Rscript", "src/causal/cs_did.R"], env=ENV, check=True)
    elif step == "honest":
        require_gate("HonestDiD bounds")
        subprocess.run(["Rscript", "src/causal/honest.R"], env=ENV, check=True)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
