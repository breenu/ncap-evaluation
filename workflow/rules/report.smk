# Stage 11: the technical report, results summary, policy brief and figure 1 slide (Phase 10; DEC-206, DEC-210).
# `report_values` writes every number the documents print (reports/_variables.yml) and their tables
# (reports/_generated/); the prose holds no typed result (tests/test_report.py). Rendering needs the separate
# site environment (envs/site-lock.yml -> ncap-site), so, like `dashboard_render`, it is not part of `all`.

REPORT_TABLES = ["hypotheses", "h1_rules", "h4", "layer_b", "robustness_a", "maiac"]
REPORT_DOCS = ["report", "summary", "policy_brief"]
REPORT_INCLUDES = ["reports/deviations.md", "reports/sources.md", "reports/references.md", "reports/appendix_b_c.md"]


rule fig1_slide:
    input:
        f"{CMP}/city_changes.parquet",
        f"{CMP}/summary.csv",
        f"{CMP}/h4.csv",
        f"{CSL}/sdid_summary.csv",
        f"{HIER}/city_shrunken.csv",
        "src/viz/fig1_decomposition.py",
        VIZ_CODE,
    output: figs("fig1_slide")
    shell: f"{PY} src.viz.fig1_decomposition --slide"


rule report_values:
    input:
        f"{STUB}/viz.done",
        "docs/figures.md",
        figs("fig1_slide"),
        f"{CSL}/sdid_summary.csv",
        f"{CSL}/robustness.csv",
        f"{CSL}/triangulation.csv",
        f"{CSL}/investigation.csv",
        f"{CSL}/levels.csv",
        f"{CSL}/layer_b/estimates.csv",
        f"{CSL}/maiac/results.json",
        f"{CSL}/maiac/exploratory_notgained.json",
        f"{HIER}/city_estimates.csv",
        f"{HIER}/pool_coefs.csv",
        f"{HIER}/city_shrunken.csv",
        f"{HIER}/h3.json",
        f"{HIER}/h5.json",
        f"{HIER}/dose_coefs.csv",
        CMP_TABLES,
        "data/processed/deweathered/family_choice.json",
        "reports/deviations.md",
        "src/report/values.py",
    output:
        "reports/_variables.yml",
        expand("reports/_generated/{t}.md", t=REPORT_TABLES),
    shell: f"{PY} src.report.values"


rule report_render:
    input:
        rules.report_values.output,
        expand("reports/{d}.qmd", d=REPORT_DOCS),
        REPORT_INCLUDES,
        "reports/_quarto.yml",
        "reports/_typst_style.typ",
    output:
        expand("reports/{d}.{ext}", d=REPORT_DOCS, ext=("pdf", "html")),
    shell: "conda run -n ncap-site --no-capture-output quarto render reports"


rule report:
    input:
        rules.report_values.output,
        expand("reports/{d}.qmd", d=REPORT_DOCS),
        REPORT_INCLUDES,
        "src/report/check.py",
    output:
        f"{STUB}/report.done",
    run:
        from src.common.gate import require_gate
        from src.report import check

        require_gate("report: every number in the Phase 10 documents")
        bad = {k: v for k, v in check.all_problems().items() if v}
        if bad:
            raise ValueError(f"report checks failed: {bad}")
        stub_done(output[0])
