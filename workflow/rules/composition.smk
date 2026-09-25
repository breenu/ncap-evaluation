# Stage 6: network-composition correction (Phase 6, RQ1).
# All stations vs balanced panel vs satellite over GHSL urban-centre boundaries.


rule composition:
    input:
        f"{STUB}/normalise.done",
    output:
        f"{STUB}/composition.done",
    run:
        stub_done(output[0])
