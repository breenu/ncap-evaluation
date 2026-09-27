# Stage 7: causal analysis (Phase 7, RQ3), plus the pre-period checks that feed the
# analysis plan (Phase 4, DEC-013, DEC-087).


# Allowed before the gate: pre-2019 data only. src/causal/pregate.py filters to year <= 2018 while
# reading and asserts it; mde_placebo.R checks again.
rule pregate_panel:
    input:
        f"{STUB}/clean.done",
        "data/processed/unit_year_sat.parquet",
        "data/processed/unit_month_sat.parquet",
        "data/processed/station_year.parquet",
        f"{INT}/sat_units.gpkg",
        f"{INT}/unit_regions.csv",
        f"{INT}/ncap_cities.csv",
        f"{INT}/ncap_funding_clean.csv",
        f"{INT}/eda/station_first_year.csv",
        f"{INT}/station_regions.csv",
        "config/params.yaml",
        "src/causal/pregate.py",
        "src/causal/treatment.py",
    output:
        f"{INT}/pregate/units.csv",
        f"{INT}/pregate/city_cohorts.csv",
        f"{INT}/pregate/pool_steps.csv",
        f"{INT}/pregate/panel_annual.parquet",
        f"{INT}/pregate/panel_season.parquet",
        f"{INT}/pregate/balance.csv",
        f"{INT}/pregate/ground_counts.csv",
        f"{INT}/pregate/ground_pairs.csv",
        f"{INT}/pregate/monitor_gain.csv",
    shell: f"{PY} src.causal.pregate"


rule pregate_mde:
    input:
        f"{INT}/pregate/panel_annual.parquet",
        f"{INT}/pregate/panel_season.parquet",
        "config/params.yaml",
        "src/causal/mde_placebo.R",
    output:
        f"{INT}/pregate/mde_draws.parquet",
        f"{INT}/pregate/placebo_actual.csv",
        f"{INT}/pregate/mde_meta.csv",
    run:
        import subprocess

        # one BLAS thread per R process: the parallel workers supply the parallelism (DEC-087)
        env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        subprocess.run(["Rscript", "src/causal/mde_placebo.R"], env=env, check=True)


rule pregate_report:
    input:
        rules.pregate_panel.output,
        rules.pregate_mde.output,
        "src/causal/pregate_report.py",
    output: "docs/pregate_checks.md"
    shell: f"{PY} src.causal.pregate_report"


# The numbers quoted in docs/analysis_plan.md must match the pipeline. The plan is hand-written
# (Reenu edits it), so it is checked, never overwritten, by the workflow.
rule pre_period_checks:
    input:
        "docs/pregate_checks.md",
        "docs/analysis_plan.md",
        "docs/analysis_plan_summary.md",
    output:
        f"{STUB}/pre_period_checks.done",
    run:
        shell(f"{PY} src.causal.pregate_report check-plan")
        stub_done(output[0])


# Gated: estimates post-2019 treatment effects (hard rule 4, DEC-012).
rule causal:
    input:
        f"{STUB}/composition.done",
        f"{STUB}/pre_period_checks.done",
    output:
        f"{STUB}/causal.done",
    run:
        from src.common.gate import require_gate

        require_gate("causal: SDID, event study, Callaway & Sant'Anna, ground ITS/DiD")
        stub_done(output[0])
