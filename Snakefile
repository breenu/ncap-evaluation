# NCAP evaluation pipeline.
#
#   snakemake --cores 8 pregate   everything allowed before the analysis plan is approved
#   snakemake --cores 8 all       full rebuild from data/raw/ to the report (needs the gate open)
#   snakemake -n all              dry run: show what would be rebuilt
#
# Phase 1: every stage is a stub that only writes a marker file under data/interim/_stubs/.
# Later phases replace each stub with real rules, keeping the stage names and order.

import os
import sys
from pathlib import Path

sys.path.insert(0, workflow.basedir)  # so rules can import src.*
# Every rule's Python writes UTF-8 to the console: GeoNames and UCDB names carry diacritics that the
# Windows default code page (cp1252) cannot encode (DEC-082).
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

configfile: "config/params.yaml"

STUB = "data/interim/_stubs"


def stub_done(path):
    """Placeholder body for a stage that is not implemented yet."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).touch()


include: "workflow/rules/acquire.smk"
include: "workflow/rules/clean.smk"
include: "workflow/rules/eda.smk"
include: "workflow/rules/normalise.smk"
include: "workflow/rules/composition.smk"
include: "workflow/rules/causal.smk"
include: "workflow/rules/hierarchical.smk"
include: "workflow/rules/viz.smk"
include: "workflow/rules/report.smk"


rule all:
    input:
        f"{STUB}/report.done",


rule pregate:
    input:
        f"{STUB}/eda.done",
        f"{STUB}/composition.done",
        f"{STUB}/pre_period_checks.done",
