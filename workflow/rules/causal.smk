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


# ---------------------------------------------------------------------------------------------------
# Phase 7 (RQ3). GATED: every module below calls require_gate() before reading post-2018 outcomes
# (hard rule 4, DEC-012). Rules DEC-138 to DEC-150. Part A = Layer A (satellite), H1/H2.

CSL = "data/processed/causal"
ES = f"{CSL}/event_study"
MAIAC = f"{CSL}/maiac"  # Phase 8b (DEC-174 to DEC-183)
SDID_A = ["primary", "v6gl03", "area", "placebo2016", "placebo2016_rm"]  # Part A specifications
SDID_B = ["v6gl0204", "towns", "towns_nopatancheruvu", "asansol_alone", "treated100k", "spill25", "funded",
          "anticip2018", "incl2020", "noigp", "restricted_pm25", "restricted_pm25_v6gl0204",
          "explore_support_minmax", "explore_support_q5_95"]  # Part B; the last two exploratory (DEC-155)
ONE_THREAD = "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1"


rule causal_era5_units:
    input:
        "data/raw/era5_monthly/MANIFEST.csv",
        f"{INT}/sat_units.gpkg",
        "src/causal/era5_units.py",
    output: f"{CSL}/era5_unit_year.parquet"
    shell: f"{PY} src.causal.era5_units"


rule causal_panels:
    input:
        f"{STUB}/pre_period_checks.done",
        "data/processed/unit_year_sat.parquet",
        "data/processed/unit_month_sat.parquet",
        f"{INT}/pregate/units.csv",
        f"{INT}/pregate/monitor_gain.csv",
        "src/causal/layer_a.py",
    output:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/panel_pre2019.parquet",
        f"{CSL}/design_units.csv",
    shell: f"{PY} src.causal.layer_a panels"


rule causal_specs:
    input:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/panel_pre2019.parquet",
        "data/processed/composition/city_changes.parquet",  # the units with a Layer B panel (DEC-150)
        "src/causal/layer_a.py",
    output:
        f"{CSL}/specs/specs.csv",
        f"{CSL}/specs/spec_units.parquet",
        f"{CSL}/specs/spec_fitsets.csv",
        f"{CSL}/specs/spec_estimands.csv",
    shell: f"{PY} src.causal.layer_a specs"


# ~1.5 h on 8 workers; resumable (replications in chunks, a spec's hash guards its outputs)
rule causal_sdid_part_a:
    input:
        rules.causal_specs.output,
        "src/causal/sdid.R",
    output: expand(f"{CSL}/sdid/{{s}}/done.txt", s=SDID_A)
    shell: f"{ONE_THREAD} {PY} src.causal.layer_a run {' '.join(SDID_A)}"


rule causal_summary:
    input:
        expand(f"{CSL}/sdid/{{s}}/done.txt", s=SDID_A + SDID_B),
    output: f"{CSL}/sdid_summary.csv"
    shell: f"{PY} src.causal.layer_a summarise"


rule causal_event_study:
    input:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/design_units.csv",
        f"{CSL}/era5_unit_year.parquet",
        "src/causal/event_study.py",
    output:
        expand(f"{ES}/{{n}}_{{f}}", n=["es_primary", "es_own2020", "es_himalayan"],
               f=["coefs.csv", "vcov.csv", "meta.json", "cohort_coefs.csv"]),
        f"{ES}/es_own2020_own.csv",
    shell: f"{PY} src.causal.event_study"


rule causal_honest:
    input:
        f"{ES}/es_primary_coefs.csv",
        f"{ES}/es_primary_vcov.csv",
        "src/causal/honest.R",
    output: expand(f"{ES}/es_primary_honest_{{f}}.csv", f=["rm", "sm", "summary"])
    shell: f"{PY} src.causal.r_steps honest"


rule causal_cs:
    input:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/design_units.csv",
        "src/causal/cs_did.R",
    output: expand(f"{CSL}/cs/cs_{{c}}_{{f}}.csv", c=["nevertreated", "notyettreated"], f=["simple", "dynamic", "attgt"])
    shell: f"{PY} src.causal.r_steps cs"


rule fig4:
    input:
        rules.causal_summary.output,
        rules.causal_event_study.output,
        rules.causal_honest.output,
        rules.causal_cs.output,
        "src/viz/fig4_event_study.py",
        "src/viz/style.py",
    output: expand("reports/figures/fig4_event_study.{ext}", ext=["png", "svg"])
    shell: f"{PY} src.viz.fig4_event_study"


rule causal_report:
    input:
        rules.causal_summary.output,
        rules.causal_event_study.output,
        rules.causal_honest.output,
        rules.causal_cs.output,
        f"{CSL}/levels.csv",
        f"{CSL}/layer_b/estimates.csv",
        f"{CSL}/triangulation.csv",
        f"{CSL}/robustness.csv",
        "data/processed/composition/entrants_summary.csv",
        f"{INT}/eda/entrants.csv",
        f"{INT}/audit/missingness_bias.csv",
        "src/causal/causal_report.py",
        "src/causal/report_part_b.py",
        "src/causal/report_maiac.py",
        f"{MAIAC}/results.json",  # Phase 8b, §12 (DEC-181)
        f"{MAIAC}/exploratory_notgained.json",  # §12f (DEC-188)
        f"{MAIAC}/weight_check.json",
        f"{MAIAC}/coverage_by_month.csv",
        "src/causal/decisions.py",
    output:
        "docs/causal_report.md",
        f"{CSL}/partA_results.json",
    shell: f"{PY} src.causal.causal_report"


# ---------------------------------------------------------------------------------------------------
# Part B: the Layer A robustness battery, Layer B, triangulation, and the review additions (DEC-147 to DEC-157)


# ~2 h on 8 workers; resumable
rule causal_sdid_part_b:
    input:
        rules.causal_specs.output,
        "src/causal/sdid.R",
    output: expand(f"{CSL}/sdid/{{s}}/done.txt", s=SDID_B)
    shell: f"{ONE_THREAD} {PY} src.causal.layer_a run {' '.join(SDID_B)}"


rule causal_loo:
    input: f"{CSL}/sdid/primary/done.txt"
    output: f"{CSL}/sdid/primary/loo.parquet"
    shell: f"{ONE_THREAD} {PY} src.causal.layer_a loo primary"


rule causal_layer_b:
    input:
        f"{DW}/station_year.parquet",
        "data/processed/composition/station_year_fitted.parquet",
        "data/processed/station_year_sat.parquet",
        f"{CSL}/design_units.csv",
        f"{CSL}/panel_annual.parquet",
        "src/causal/layer_b.py",
    output:
        expand(f"{CSL}/layer_b/{{f}}", f=["estimates.csv", "its_cities.csv", "misfit_by_year.csv", "satellite_at_stations.csv"]),
    shell: f"{PY} src.causal.layer_b"


rule causal_descriptive:
    input:
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/design_units.csv",
        "src/causal/descriptive.py",
    output: f"{CSL}/levels.csv"
    shell: f"{PY} src.causal.descriptive"


rule figS1:
    input:
        f"{CSL}/levels.csv",
        "src/viz/figS1_levels.py",
        "src/viz/style.py",
    output: expand("reports/figures/figS1_levels.{ext}", ext=["png", "svg"])
    shell: f"{PY} src.viz.figS1_levels"


rule causal_triangulation:
    input:
        f"{CSL}/sdid_summary.csv",
        f"{CSL}/layer_b/estimates.csv",
        f"{CSL}/layer_b/satellite_at_stations.csv",
        "data/processed/composition/trends.parquet",
        f"{MAIAC}/sdid_summary.csv",  # Phase 8b: investigation step 2 (DEC-181)
        "src/causal/triangulation.py",
        "src/causal/report_maiac.py",
        "src/causal/decisions.py",
    output:
        f"{CSL}/triangulation.csv",
        f"{CSL}/investigation.csv",
    shell: f"{PY} src.causal.triangulation"


# The registered fire-covariate check (DEC-171), run 2026-10-03 once FIRMS was downloaded (DEC-039)
rule causal_fire_covariate:
    input:
        "data/raw/firms/MANIFEST.csv",  # the 2012-2024 archive (the 2025+ API part is not used; DEC-172)
        f"{CSL}/design_units.csv",
        f"{INT}/sat_units.gpkg",
        "src/causal/fire.py",
    output: f"{CSL}/fire_unit_year.parquet"
    shell: f"{PY} src.causal.fire covariate"


rule causal_fire:
    input:
        f"{CSL}/fire_unit_year.parquet",
        f"{CSL}/panel_annual.parquet",
        f"{CSL}/era5_unit_year.parquet",
        "src/causal/event_study.py",
        "src/causal/fire.py",
    output: expand(f"{ES}/{{n}}_{{f}}", n=["es_fire", "es_fire_window"], f=["coefs.csv", "meta.json"])
    shell: f"{PY} src.causal.fire run"


rule causal_robustness:
    input:
        rules.causal_fire.output,
        f"{CSL}/sdid_summary.csv",
        f"{CSL}/sdid/primary/loo.parquet",
        f"{CSL}/layer_b/estimates.csv",
        rules.causal_event_study.output,
        rules.causal_cs.output,
        f"{MAIAC}/results.json",  # Phase 8b (DEC-181)
        "src/causal/robustness.py",
        "src/causal/report_maiac.py",
        "src/causal/decisions.py",
    output: f"{CSL}/robustness.csv"
    shell: f"{PY} src.causal.robustness"


# Phase 8b: the registered raw MAIAC AOD check (DEC-174 to DEC-183). The Earth Engine export needs Reenu's
# credentials, so it is run on request:  python -m src.acquire.maiac_gee check | pilot | submit | download


rule causal_maiac_panels:
    input:
        "data/raw/maiac_gee/MANIFEST.csv",
        f"{CSL}/design_units.csv",
        f"{CSL}/panel_annual.parquet",
        "data/processed/unit_year_sat.parquet",
        "config/maiac.yaml",
        "src/causal/maiac.py",
    output:
        f"{MAIAC}/panel_aod.parquet",
        f"{MAIAC}/unit_month.parquet",
        f"{MAIAC}/unit_year.parquet",
        f"{MAIAC}/sample.csv",
        f"{MAIAC}/coverage_by_month.csv",
        f"{MAIAC}/weight_check.json",
    shell: f"{PY} src.causal.maiac panels"


rule causal_maiac_specs:
    input:
        f"{MAIAC}/panel_aod.parquet",
        f"{MAIAC}/sample.csv",
        "data/processed/composition/city_changes.parquet",
        "src/causal/maiac.py",
        "src/causal/layer_a.py",
    output:
        f"{MAIAC}/specs/specs.csv",
        f"{MAIAC}/specs/spec_units.parquet",
        f"{MAIAC}/specs/spec_fitsets.csv",
        f"{MAIAC}/specs/spec_estimands.csv",
        f"{MAIAC}/specs/yardsticks.json",
    shell: f"{PY} src.causal.maiac specs"


# ~2 h on 8 workers, on mains power (DEC-168); resumable. Which yardstick specs exist depends on the sample,
# so the rule runs every spec in specs.csv; the module writes one flag when all are done.
rule causal_maiac_sdid:
    input:
        rules.causal_maiac_specs.output,
        "src/causal/sdid.R",
    output: f"{MAIAC}/sdid/all.done"
    shell: f"{PY} src.causal.maiac run"  # one BLAS thread per worker is set inside (layer_a.run); writes the flag


rule causal_maiac_event:
    input:
        f"{MAIAC}/specs/spec_units.parquet",
        f"{MAIAC}/panel_aod.parquet",
        f"{CSL}/era5_unit_year.parquet",
        "src/causal/maiac.py",
        "src/causal/event_study.py",
    output: f"{MAIAC}/event_study/es_aod_coefs.csv", f"{MAIAC}/event_study/es_aod_meta.json"
    shell: f"{PY} src.causal.maiac event"


rule causal_maiac_summary:
    input:
        f"{MAIAC}/sdid/all.done",
        rules.causal_maiac_event.output,
        "src/causal/maiac.py",
        "src/causal/decisions.py",
    output: f"{MAIAC}/results.json", f"{MAIAC}/sdid_summary.csv", f"{MAIAC}/exploratory_notgained.json"  # last: DEC-188
    shell: f"{PY} src.causal.maiac summarise"


# Figure 1 with the Phase 7 step (DEC-150): its own output name, so the Phase 6 figure rule stays ungated
rule fig1_policy:
    input:
        f"{CSL}/sdid_summary.csv",
        f"{CSL}/layer_b/estimates.csv",
        "data/processed/composition/summary.csv",
        "data/processed/composition/h4.csv",
        "src/viz/fig1_decomposition.py",
        "src/viz/style.py",
    output: expand("reports/figures/fig1_decomposition_policy.{ext}", ext=["png", "svg"])
    shell: f"{PY} src.viz.fig1_decomposition --policy"


rule causal:
    input:
        f"{STUB}/composition.done",
        f"{STUB}/pre_period_checks.done",
        "docs/causal_report.md",
        expand("reports/figures/{f}.{ext}", f=["fig4_event_study", "figS1_levels", "fig1_decomposition_policy"], ext=["png", "svg"]),
    output:
        f"{STUB}/causal.done",
    run:
        from src.common.gate import require_gate

        require_gate("causal: SDID, event study, Callaway & Sant'Anna, ground ITS/DiD")
        stub_done(output[0])
