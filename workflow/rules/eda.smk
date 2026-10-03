# Stage 4: exploratory analysis tables (Phase 3) and the generated audit report. Figures 2, 8 and E1-E4
# are drawn in viz.smk (DEC-190). Blinding rule until the gate: nothing here compares NCAP vs non-NCAP units.

rule eda_figures:
    input:
        f"{STUB}/clean.done",
        "data/processed/station_year_quality.parquet",
        "data/processed/unit_month_sat.parquet",
        "src/viz/eda.py",
    output:
        "data/processed/station_year.parquet",
        # written by src/viz/eda.py since Phase 3 but first declared in Phase 7 (DEC-158), when a gated rule
        # first made a clean clone's DAG need them (pregate_panel reads station_first_year.csv)
        expand(f"{INT}/eda/{{f}}.csv", f=["station_first_year", "entrants", "ground_vs_satellite", "seasonal_ground",
                                            "seasonal_satellite", "city_trends"]),
    shell: f"{PY} src.viz.eda"


rule audit_report:
    input:
        "data/processed/station_year.parquet",
        f"{INT}/audit/missingness_models.csv",
        "src/clean/audit_report.py",
    output: "docs/audit_report.md"
    shell: f"{PY} src.clean.audit_report"


rule eda:
    input:
        "docs/audit_report.md",
    output:
        f"{STUB}/eda.done",
    run:
        stub_done(output[0])
