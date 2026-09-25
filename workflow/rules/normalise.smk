# Stage 5: meteorological normalisation / deweathering (Phase 5, RQ2).


rule normalise:
    input:
        f"{STUB}/clean.done",
    output:
        f"{STUB}/normalise.done",
    run:
        stub_done(output[0])
