# Stage 8: heterogeneity and mechanism (Phase 8, RQ4).


# Gated: pools post-2019 city effect estimates.
rule hierarchical:
    input:
        f"{STUB}/causal.done",
    output:
        f"{STUB}/hierarchical.done",
    run:
        from src.common.gate import require_gate

        require_gate("hierarchical: pooled city effects, dose-response, PM10 vs PM2.5")
        stub_done(output[0])
