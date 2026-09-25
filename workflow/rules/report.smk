# Stage 11: Quarto technical report, results summary and policy brief (Phase 10).


rule report:
    input:
        f"{STUB}/viz.done",
    output:
        f"{STUB}/report.done",
    run:
        stub_done(output[0])
