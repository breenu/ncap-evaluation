# Stage 10: the eight report figures and the precomputed dashboard data (Phase 9).


rule viz:
    input:
        f"{STUB}/eda.done",
        f"{STUB}/hierarchical.done",
    output:
        f"{STUB}/viz.done",
    run:
        stub_done(output[0])
