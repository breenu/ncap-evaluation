# Stage 4: exploratory analysis, station-entry map, data-quality heatmap (Phase 3).
# Blinding rule until the gate: nothing here compares NCAP vs non-NCAP units after 2018.


rule eda:
    input:
        f"{STUB}/clean.done",
    output:
        f"{STUB}/eda.done",
    run:
        stub_done(output[0])
