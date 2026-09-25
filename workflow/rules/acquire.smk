# Stage 1: data acquisition (Phase 2). One rule per source in src/acquire/.
# Raw files land in data/raw/<source>/ with a MANIFEST.csv (src/common/manifest.py).


rule acquire:
    output:
        f"{STUB}/acquire.done",
    run:
        stub_done(output[0])
