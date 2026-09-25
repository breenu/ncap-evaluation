# Stages 2-3: Parquet storage, cleaning and the station audit (Phase 3, RQ1).


rule clean:
    input:
        f"{STUB}/acquire.done",
    output:
        f"{STUB}/clean.done",
    run:
        stub_done(output[0])
