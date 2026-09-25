# Stage 7: causal analysis (Phase 7, RQ3), plus the pre-period checks that feed the
# analysis plan (Phase 4, DEC-013).


# Allowed before the gate: uses pre-2019 data only (MDE by placebo-in-time, baseline balance).
rule pre_period_checks:
    input:
        f"{STUB}/clean.done",
    output:
        f"{STUB}/pre_period_checks.done",
    run:
        stub_done(output[0])


# Gated: estimates post-2019 treatment effects (hard rule 4, DEC-012).
rule causal:
    input:
        f"{STUB}/composition.done",
        f"{STUB}/pre_period_checks.done",
    output:
        f"{STUB}/causal.done",
    run:
        from src.common.gate import require_gate

        require_gate("causal: SDID, event study, Callaway & Sant'Anna, ground ITS/DiD")
        stub_done(output[0])
