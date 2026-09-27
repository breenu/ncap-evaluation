"""docs/pregate_checks.md: the Phase 4 pre-gate numbers (MDE, control pool, balance, ground PM10
feasibility), generated from data/interim/pregate/. Also fills the numbers quoted in
docs/analysis_plan.md, so no number in the plan is typed by hand (CLAUDE.md hard rule 3).

The plan marks every generated number as <!--g:key-->value<!--/g--> (inline or a whole block).

    python -m src.causal.pregate_report             # write docs/pregate_checks.md
    python -m src.causal.pregate_report sync-plan   # rewrite the marked values in the plan and its summary
    python -m src.causal.pregate_report check-plan  # fail if any marked value is stale (pipeline step)

PRE-PERIOD ONLY: every input was built from data up to 2018 (src/causal/pregate.py, mde_placebo.R).
"""

import re
import sys

import numpy as np
import pandas as pd

from src.causal.pregate import OUT, assert_pre_period
from src.common.paths import DOCS, params

MARK = re.compile(r"<!--g:(\w+)-->(.*?)<!--/g-->", re.DOTALL)
PLAN = DOCS / "analysis_plan.md"
# Files whose marked numbers sync-plan fills and check-plan verifies.
PLAN_FILES = [PLAN, DOCS / "analysis_plan_summary.md"]
REPORT = DOCS / "pregate_checks.md"
OUTCOMES = {
    "log_annual": "Annual PM2.5, log (primary)",
    "level_annual": "Annual PM2.5, level (µg/m³)",
    "log_winter": "Winter PM2.5 (Oct-Feb), log",
    "log_nonwinter": "Non-winter PM2.5 (Mar-Sep), log",
    "winter_minus_nonwinter": "Winter minus non-winter, log (H2)",
}
DESIGNS = {"random": "random", "region_matched": "region-matched"}
# The real treated set's placebo takes its SE from the null that shares its regional make-up.
ACTUAL_NULL = "region_matched"


# Display convention (fixed after Reenu's Phase 4 review, DEC-091): log-scale quantities are shown
# in natural-log units (0.01 = a 1% change, approximately), never as "log points", with the implied
# percentage beside them where it matters.


def pct_reduction(log_units: float) -> float:
    """A fall of `log_units` (natural-log units) as a percentage reduction."""
    return 100 * (1 - np.exp(-log_units))


def pct_change(log_units: float) -> float:
    """A change of `log_units` (natural-log units) as a signed percentage change."""
    return 100 * np.expm1(log_units)


def lg(x: float) -> str:
    """A natural-log quantity, 4 decimals, signed."""
    return f"{x:+.4f}"


def pc(x: float) -> str:
    """The signed percentage change implied by a natural-log quantity."""
    return f"{pct_change(x):+.2f}%"


def p_equal_tailed(null: pd.Series, att: float) -> float:
    """Two-sided permutation p from the empirical null, without assuming it is centred on zero."""
    n = len(null)
    lo = (1 + (null <= att).sum()) / (1 + n)
    hi = (1 + (null >= att).sum()) / (1 + n)
    return float(min(1.0, 2 * min(lo, hi)))


def fmt(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}"


def md(df: pd.DataFrame) -> str:
    head = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return head + "\n".join(
        "| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)
    )


# ---------------------------------------------------------------- computations


def wide_draws(draws: pd.DataFrame) -> pd.DataFrame:
    """One row per design, draw and fake year; one column per outcome, plus winter minus non-winter."""
    d = draws.pivot_table(
        index=["design", "draw", "fake_year"], columns="outcome", values="att"
    ).reset_index()
    d["winter_minus_nonwinter"] = d.log_winter - d.log_nonwinter
    return d


def mde_table(draws: pd.DataFrame, mult: float) -> pd.DataFrame:
    """SE (SD of placebo ATTs over random treated sets), bias, percentiles and MDE per design, outcome and fake year."""
    long = wide_draws(draws).melt(
        id_vars=["design", "draw", "fake_year"], var_name="outcome", value_name="att"
    )
    g = long.groupby(["design", "outcome", "fake_year"]).att
    t = pd.DataFrame({"draws": g.size(), "mean": g.mean(), "se": g.std(ddof=1),
                      "q025": g.quantile(0.025), "q975": g.quantile(0.975)}).reset_index()  # fmt: skip
    t["mde"] = mult * t.se
    return t


def actual_table(
    actual: pd.DataFrame, draws: pd.DataFrame, design: str = ACTUAL_NULL
) -> pd.DataFrame:
    """The real treated set at the fake years: ATT, SE from one design's null draws, 95% CI, permutation p."""
    a = actual.pivot_table(index="fake_year", columns="outcome", values="att")
    a["winter_minus_nonwinter"] = a.log_winter - a.log_nonwinter
    a = a.reset_index().melt(id_vars="fake_year", var_name="outcome", value_name="att")
    d = wide_draws(draws)
    d = d[d.design == design]
    rows = []
    for r in a.itertuples(index=False):
        null = d.loc[d.fake_year == r.fake_year, r.outcome]
        se = null.std(ddof=1)
        p = p_equal_tailed(null, r.att)
        rows.append({"outcome": r.outcome, "fake_year": r.fake_year, "att": r.att, "se": se,
                     "lo": r.att - 1.96 * se, "hi": r.att + 1.96 * se, "p_perm": p})  # fmt: skip
    return pd.DataFrame(rows)


def load() -> dict:
    meta = pd.read_csv(OUT / "mde_meta.csv").iloc[0]
    if meta.last_year > params()["pregate"]["last_year"]:
        raise RuntimeError("MDE inputs extend past the pre-period")
    draws = pd.read_parquet(OUT / "mde_draws.parquet")
    actual = pd.read_csv(OUT / "placebo_actual.csv")
    assert_pre_period(draws, "fake_year")
    units = pd.read_csv(OUT / "units.csv")
    ann = pd.read_parquet(OUT / "panel_annual.parquet")
    assert_pre_period(ann)
    return {
        "annual": ann,
        "meta": meta,
        "draws": draws,
        "mde": mde_table(draws, params()["pregate"]["mde_multiplier"]),
        "actual": actual_table(actual, draws),
        "units": units,
        "pool": pd.read_csv(OUT / "pool_steps.csv"),
        "balance": pd.read_csv(OUT / "balance.csv"),
        "gcounts": pd.read_csv(OUT / "ground_counts.csv"),
        "gpairs": pd.read_csv(OUT / "ground_pairs.csv"),
        "cities": pd.read_csv(OUT / "city_cohorts.csv"),
        "gain": pd.read_csv(OUT / "monitor_gain.csv"),
    }


# ---------------------------------------------------------------- tables shared by the report and the plan


def mde_block(D: dict) -> str:
    t = (
        D["mde"]
        .assign(order=lambda x: x.outcome.map(list(OUTCOMES).index))
        .sort_values(["order", "fake_year", "design"])
    )
    rows = []
    for r in t.itertuples():
        level = r.outcome == "level_annual"
        diff = r.outcome == "winter_minus_nonwinter"
        rows.append({
            "Outcome": OUTCOMES[r.outcome],
            "Null design": DESIGNS[r.design],
            "Fake adoption": r.fake_year,
            "SE": fmt(r.se, 2) + " µg/m³" if level else f"{r.se:.4f}",
            "Mean placebo ATT": f"{r.mean:+.2f} µg/m³" if level else lg(r.mean),
            "MDE": (fmt(r.mde, 2) + " µg/m³") if level else
                   (f"{r.mde:.4f} (≈ {fmt(100 * r.mde, 1)} pp)" if diff else f"{r.mde:.4f} ({fmt(pct_reduction(r.mde), 1)}% fall)"),
        })  # fmt: skip
    return md(pd.DataFrame(rows))


def primary_mde(D: dict, outcome: str) -> float:
    """The MDE carried into the decision rules: the largest (most conservative) over null designs and fake years."""
    t = D["mde"]
    return float(t[t.outcome == outcome].mde.max())


def balance_block(D: dict) -> str:
    b = D["balance"]
    rows = []
    for r in b.itertuples(index=False):
        share = r.characteristic.startswith("Region")
        f = (lambda v: fmt(100 * v, 1) + "%") if share else (lambda v: fmt(v, 2))
        rows.append({"Characteristic (2010-2018 unless stated)": r.characteristic.replace("ug/m3", "µg/m³"),
                     f"NCAP units (n={r.n_treated})": f(r.treated),
                     f"Control pool (n={r.n_control_pool})": f(r.control_pool),
                     "SMD": fmt(r.smd_vs_control_pool, 2),
                     f"Buffered pool (n={r.n_buffered_pool})": f(r.buffered_pool),
                     "SMD (buffered)": fmt(r.smd_vs_buffered_pool, 2)})  # fmt: skip
    return md(pd.DataFrame(rows))


def pool_block(D: dict) -> str:
    p = D["pool"].copy()
    p["units"] = p.units.map(lambda v: f"{v:,}")
    return md(p.rename(columns={"step": "Rule", "units": "Units"}))


def actual_block(D: dict) -> str:
    a = D["actual"]
    a = a[a.outcome.isin(["log_annual", "level_annual", "winter_minus_nonwinter"])]
    rows = []
    for r in a.itertuples(index=False):
        level = r.outcome == "level_annual"
        if level:
            att, ci = f"{r.att:+.2f} µg/m³", f"{r.lo:+.2f} to {r.hi:+.2f} µg/m³"
        elif r.outcome == "winter_minus_nonwinter":
            pp = lambda x: f"{100 * x:+.2f} pp"  # noqa: E731
            att, ci = (
                f"{lg(r.att)} ({pp(r.att)})",
                f"{lg(r.lo)} to {lg(r.hi)} ({pp(r.lo)} to {pp(r.hi)})",
            )
        else:
            att, ci = (
                f"{lg(r.att)} ({pc(r.att)})",
                f"{lg(r.lo)} to {lg(r.hi)} ({pc(r.lo)} to {pc(r.hi)})",
            )
        rows.append({"Outcome": OUTCOMES[r.outcome], "Fake adoption": r.fake_year, "Placebo ATT": att,
                     "95% CI": ci, "Permutation p (equal-tailed)": fmt(r.p_perm, 3)})  # fmt: skip
    return md(pd.DataFrame(rows))


def ground_block(D: dict) -> str:
    c = D["gcounts"][D["gcounts"].pollutant == "pm10"]
    w = c.pivot_table(index="year", columns="group", values="station_years", fill_value=0).astype(
        int
    )
    u = c.pivot_table(index="year", columns="group", values="units", fill_value=0).astype(int)
    w = w.reindex(columns=["NCAP unit", "non-NCAP unit"], fill_value=0)
    u = u.reindex(index=w.index, columns=["NCAP unit", "non-NCAP unit"], fill_value=0)
    t = pd.DataFrame({"Year": w.index,
                      "NCAP: station-years (units)": [f"{a} ({b})" for a, b in zip(w["NCAP unit"], u["NCAP unit"], strict=True)],
                      "Non-NCAP: station-years (units)": [f"{a} ({b})" for a, b in zip(w["non-NCAP unit"], u["non-NCAP unit"], strict=True)]})  # fmt: skip
    return md(t)


def level_reconciliation(D: dict) -> dict[str, str]:
    """Why the level-scale MDE (µg/m³) is larger than the log-scale MDE times the mean level.

    Year-to-year noise per control unit (SD of residuals from its own 2010-2018 linear trend), by
    tercile of mean PM2.5: absolute (µg/m³) noise grows with the level much faster than
    proportional (log) noise, so a µg/m³-scale estimate is dominated by the dirtiest units.
    """
    ann, mde = D["annual"], D["mde"]
    ctl = ann[ann.role == "control"]

    def resid_sd(y, x):
        return float(np.std(y - np.polyval(np.polyfit(x, y, 1), x), ddof=2))

    r = ctl.groupby("unit_id").apply(
        lambda g: pd.Series({"mean": g.pm25_popw.mean(),
                             "sd_log": resid_sd(np.log(g.pm25_popw), g.year),
                             "sd_lvl": resid_sd(g.pm25_popw, g.year)}),
        include_groups=False,
    )  # fmt: skip
    r["tercile"] = pd.qcut(r["mean"], 3, labels=["cleanest", "middle", "dirtiest"])
    m = r.groupby("tercile", observed=True)[["mean", "sd_log", "sd_lvl"]].median()
    share = (r.sd_lvl**2)[r.tercile == "dirtiest"].sum() / (r.sd_lvl**2).sum()
    se = mde.pivot_table(index=["design", "fake_year"], columns="outcome", values="se")
    ratio = se.level_annual / (se.log_annual * ctl.pm25_popw.mean())
    return {
        "recon_lvl_ratio_lo": fmt(ratio.min(), 1),
        "recon_lvl_ratio_hi": fmt(ratio.max(), 1),
        "recon_clean_mean": fmt(m.loc["cleanest", "mean"], 0),
        "recon_dirty_mean": fmt(m.loc["dirtiest", "mean"], 0),
        "recon_lvl_sd_ratio": fmt(m.loc["dirtiest", "sd_lvl"] / m.loc["cleanest", "sd_lvl"], 1),
        "recon_log_sd_ratio": fmt(m.loc["dirtiest", "sd_log"] / m.loc["cleanest", "sd_log"], 1),
        "recon_dirty_share": fmt(100 * share, 0),
    }


# ---------------------------------------------------------------- values quoted in the plan


def plan_values(D: dict) -> dict[str, str]:
    u, pool, meta = D["units"], D["pool"].set_index("step").units, D["meta"]
    tr = u[u.role == "treated"]
    bal = D["balance"].set_index("characteristic")
    gc = D["gcounts"].set_index(["pollutant", "year", "group"])
    gp = D["gpairs"].set_index(["pollutant", "years", "group"])
    act = D["actual"].set_index(["outcome", "fake_year"])
    fy = [int(y) for y in params()["pregate"]["fake_adoption_years"]]
    first, last = int(meta.first_year), int(meta.last_year)

    def gcount(pol, year, grp, col="station_years"):
        return int(gc[col].get((pol, year, grp), 0))

    trend = bal.loc[f"PM2.5 trend {first}-{last} (% per year)"]
    v = {
        "n_treated": f"{len(tr)}",
        "n_controls": f"{int((u.role == 'control').sum())}",
        "n_buffered": f"{int(u.in_buffered_pool.sum())}",
        "n_nonncap": f"{int(pool['Non-NCAP centres']):,}",
        "n_pop": f"{int(pool['... with 2015 population >= 100,000'])}",
        "n_below_100k_treated": f"{int((tr.pop_2015 < params()['control_pool']['min_population']).sum())}",
        "draws": f"{int(meta.draws)}",
        "coh_2019": f"{int((tr.cohort_listed == 2019).sum())}",
        "coh_2020": f"{int((tr.cohort_listed == 2020).sum())}",
        "coh_2021": f"{int((tr.cohort_listed == 2021).sum())}",
        "fcoh_2020": f"{int((tr.cohort_funded == 2020).sum())}",
        "fcoh_2021": f"{int((tr.cohort_funded == 2021).sum())}",
        "fcoh_2022": f"{int((tr.cohort_funded == 2022).sum())}",
        "mde_pct": fmt(pct_reduction(primary_mde(D, "log_annual")), 1),
        "mde_log": f"{primary_mde(D, 'log_annual'):.4f}",
        "mde_ugm3": fmt(primary_mde(D, "level_annual"), 1),
        "mde_ugm3_implied": fmt(
            pct_reduction(primary_mde(D, "log_annual"))
            / 100
            * bal.loc[f"PM2.5 mean {first}-{last} (ug/m3)"].treated,
            1,
        ),
        "mde_winter_pct": fmt(pct_reduction(primary_mde(D, "log_winter")), 1),
        "mde_nonwinter_pct": fmt(pct_reduction(primary_mde(D, "log_nonwinter")), 1),
        "mde_h2_log": f"{primary_mde(D, 'winter_minus_nonwinter'):.4f}",
        "mde_h2_pp": fmt(100 * primary_mde(D, "winter_minus_nonwinter"), 1),
        "trend_treated": fmt(trend.treated, 1),
        "trend_control": fmt(trend.control_pool, 1),
        "smd_pop": fmt(bal.loc["Population 2015 (log10)"].smd_vs_control_pool, 2),
        "igp_treated": fmt(100 * bal.loc["Region: igp"].treated, 0),
        "igp_control": fmt(100 * bal.loc["Region: igp"].control_pool, 0),
        "level_treated": fmt(bal.loc[f"PM2.5 mean {first}-{last} (ug/m3)"].treated, 1),
        "level_control": fmt(bal.loc[f"PM2.5 mean {first}-{last} (ug/m3)"].control_pool, 1),
        "pm10_2017_ncap": f"{gcount('pm10', 2017, 'NCAP unit')}",
        "pm10_2017_non": f"{gcount('pm10', 2017, 'non-NCAP unit')}",
        "pm10_2018_ncap": f"{gcount('pm10', 2018, 'NCAP unit')}",
        "pm10_2018_ncap_units": f"{gcount('pm10', 2018, 'NCAP unit', 'units')}",
        "pm10_2018_non": f"{gcount('pm10', 2018, 'non-NCAP unit')}",
        "pm10_pair_stations": f"{int(gp.stations.get(('pm10', f'{last - 1}-{last}', 'NCAP unit'), 0))}",
        "pm10_pair_units": f"{int(gp.units.get(('pm10', f'{last - 1}-{last}', 'NCAP unit'), 0))}",
        "pm10_pair_non": f"{int(gp.stations.get(('pm10', f'{last - 1}-{last}', 'non-NCAP unit'), 0))}",
        "table_mde": "\n\n" + mde_block(D) + "\n\n",
        "table_balance": "\n\n" + balance_block(D) + "\n\n",
        "table_pool": "\n\n" + pool_block(D) + "\n\n",
        "table_placebo_actual": "\n\n" + actual_block(D) + "\n\n",
        "table_ground": "\n\n" + ground_block(D) + "\n\n",
    }
    logs = D["mde"][D["mde"].outcome.isin(["log_annual", "log_winter", "log_nonwinter"])]
    worst = logs.loc[logs["mean"].abs().idxmax()]
    v["null_offset_log"] = lg(worst["mean"])
    v["null_offset_pct"] = pc(worst["mean"])
    short = {"log_annual": "annual", "log_winter": "winter", "log_nonwinter": "non-winter"}
    v["null_offset_where"] = (
        f"{DESIGNS[worst.design]} sets, {short[worst.outcome]} PM2.5, fake adoption {int(worst.fake_year)}"
    )
    v["null_offset_mcse"] = f"{worst.se / np.sqrt(worst.draws):.4f}"
    v.update(level_reconciliation(D))
    R, g = params()["robustness"], D["gain"]
    v["equiv_margin"] = f"{R['equivalence_margin_pct']:g}"
    v["leak_from"], v["leak_to"] = (str(y) for y in R["leakage_gain_years"])
    v["leak_min"] = f"{R['leakage_min_units']}"
    v["leak_gain"] = f"{int(g.gained_monitor.sum())}"
    v["leak_nogain"] = f"{int((~g.gained_monitor).sum())}"
    v["leak_nogain_had"] = f"{int((~g.gained_monitor & (g.stations_before > 0)).sum())}"
    v["leak_nogain_never"] = f"{int((~g.gained_monitor & (g.stations_before == 0)).sum())}"
    small = [name for name, k in [("gained", "leak_gain"), ("did not gain", "leak_nogain")]
             if int(v[k]) < R["leakage_min_units"]]  # fmt: skip
    v["leak_estimable"] = (
        "both groups are large enough to estimate"
        if not small
        else "too small to estimate: the group that " + " / ".join(small) + " a monitor"
    )
    for y in fy:
        a = act.loc[("log_annual", y)]
        v[f"placebo_{y}_pct"] = pc(a.att)
        v[f"placebo_{y}_ci"] = f"{pc(a.lo)} to {pc(a.hi)}"
        v[f"placebo_{y}_p"] = fmt(a.p_perm, 2)
    return v


def fill(text: str, values: dict[str, str]) -> str:
    """Replace every marked value in `text`; unknown keys are an error."""

    def sub(m):
        if m.group(1) not in values:
            raise KeyError(f"analysis_plan.md marks unknown key '{m.group(1)}'")
        return f"<!--g:{m.group(1)}-->{values[m.group(1)]}<!--/g-->"

    return MARK.sub(sub, text)


def stale(text: str, values: dict[str, str]) -> list[str]:
    return [m.group(1) for m in MARK.finditer(text) if values.get(m.group(1)) != m.group(2)]


# ---------------------------------------------------------------- report


def build(D: dict) -> str:
    P, V, meta = params(), plan_values(D), D["meta"]
    fy = [int(y) for y in P["pregate"]["fake_adoption_years"]]
    L = ["# Pre-gate checks (Phase 4)", "",
         "*Generated by `python -m src.causal.pregate_report` from `data/interim/pregate/`. Do not edit by hand. "
         f"**Pre-period only:** every input was read with year ≤ {P['pregate']['last_year']} enforced in the reader "
         "(`src/causal/pregate.py`) and checked again in `src/causal/mde_placebo.R`. Nothing here compares NCAP "
         "with non-NCAP units after 2018.*", ""]  # fmt: skip

    L += ["## 1. Units and control pool", "",
          f"Units are GHSL urban centres (satellite Layer A). Treated: every centre holding an NCAP city ({V['n_treated']}). "
          "Control pool: non-NCAP centres with 2015 population ≥ 100,000, minus any centre that contains the point of an "
          "NCAP town with no centre of its own (Kalka, which contains Parwanoo; DEC-063). The spillover buffer is a "
          f"sensitivity analysis: controls closer than {P['control_pool']['spillover_buffer_km']} km (edge to edge) to any "
          "NCAP place, including the 10 buffered towns, are dropped.", "",
          V["table_pool"].strip(), ""]  # fmt: skip

    L += ["## 2. Treatment cohorts (treated units)", "",
          "Primary: the date a city first appears on an official list; listed by 30 June counts from that year, "
          "nothing before 2019. Alternative: first financial year with a recorded central release, counted from the "
          "next calendar year (DEC-086). A shared unit takes its earliest member.", "",
          md(pd.DataFrame({"Cohort": [2019, 2020, 2021, 2022],
                           "Listed (primary)": [V["coh_2019"], V["coh_2020"], V["coh_2021"], "0"],
                           "Funded (alternative)": ["0", V["fcoh_2020"], V["fcoh_2021"], V["fcoh_2022"]]})),
          "", "Funding-date evidence per city: " + ", ".join(f"{k}: {v}" for k, v in D["cities"].fy_source.value_counts().items()) + ".", ""]  # fmt: skip

    L += ["## 3. Baseline balance, 2010-2018", "",
          "Unweighted means; SMD = standardised mean difference (treated minus control, pooled SD). |SMD| > 0.25 is "
          "a conventional sign of imbalance. SDID does not need levels to balance (unit effects absorb them) but "
          "does need comparable trends; its unit weights target the pre-period path, which §5 tests.", "",
          V["table_balance"].strip(), ""]  # fmt: skip

    L += ["## 4. Minimum detectable effect (primary satellite SDID)", "",
          f"Placebo-in-time on {int(meta.first_year)}-{int(meta.last_year)} (seasons {int(meta.season_first)}-{int(meta.season_last)}), "
          f"V5.GL.06 population-weighted PM2.5. For each of {V['draws']} sets of {V['n_treated']} control units "
          f"(the size of the real treated set), treatment is assigned from a fake year ({', '.join(map(str, fy))}) and "
          f"SDID is estimated against the other {int(meta.n_controls) - int(meta.n_treated)} controls. SE = SD of the "
          f"placebo ATTs; MDE = {P['pregate']['mde_multiplier']} × SE (5% two-sided, 80% power). The same draws serve "
          "every outcome.", "",
          "**Units.** Log-scale quantities are in natural-log units: 0.0100 is about a 1% change (exactly, "
          "100 × (e^x − 1)%). The MDE column also gives the percentage fall this implies. For winter minus "
          "non-winter, \"pp\" is percentage points (100 × the difference of two log effects).", "",
          "Two null designs: **random** sets (any controls) and **region-matched** sets (as many controls from each "
          "region as the real treated set has). Random sets are scattered across India and average away regional "
          "shocks that a real, regionally clustered treated set carries; matching the regional make-up brings the null "
          "closer to the real design.", "",
          V["table_mde"].strip(), "",
          f"**Carried into the plan** (the largest over both designs and both fake years): annual PM2.5 **{V['mde_pct']}% fall** "
          f"({V['mde_log']} in log units), which at the NCAP units' 2010-2018 mean of {V['level_treated']} µg/m³ is "
          f"**{V['mde_ugm3_implied']} µg/m³**; winter {V['mde_winter_pct']}%, non-winter {V['mde_nonwinter_pct']}%; "
          f"winter minus non-winter {V['mde_h2_log']} in log units (≈ {V['mde_h2_pp']} percentage points).", "",
          f"**Why the µg/m³-scale MDE is larger ({V['mde_ugm3']} µg/m³).** It comes from a separate SDID fit on the "
          "µg/m³ scale, not from converting the % MDE. That fit's SE is "
          f"{V['recon_lvl_ratio_lo']}-{V['recon_lvl_ratio_hi']} times the log-scale SE multiplied by the pool's mean level, "
          "because absolute noise is concentrated in the most polluted units. Per control unit, year-to-year noise "
          f"around its own 2010-2018 trend is {V['recon_lvl_sd_ratio']} times larger in µg/m³ in the dirtiest third "
          f"(median {V['recon_dirty_mean']} µg/m³) than in the cleanest third (median {V['recon_clean_mean']} µg/m³), but only "
          f"{V['recon_log_sd_ratio']} times larger in proportional terms; the dirtiest third holds {V['recon_dirty_share']}% "
          "of the µg/m³ noise variance. The primary outcome is on the log scale, so the % MDE is the one the plan uses.", "",
          f"**Offset in the null.** Region-matched placebo sets are not centred exactly on zero: the largest mean placebo "
          f"ATT is {V['null_offset_log']} in log units ({V['null_offset_pct']}; {V['null_offset_where']}), against a Monte "
          f"Carlo error of about {V['null_offset_mcse']}. SDID carries a small bias when the treated set shares a "
          "regional structure the donors lack; it is below one SE and is reported, not corrected. Because this null is "
          "not centred on zero, permutation p-values are equal-tailed (twice the smaller tail share), not based on "
          "|ATT|.", "",
          "Percentiles of the null draws (a check that the SD is a fair summary):", "",
          md(D["mde"].assign(**{"2.5%": lambda t: t.q025.map(lg), "97.5%": lambda t: t.q975.map(lg)})
             [lambda t: t.outcome != "level_annual"][["design", "outcome", "fake_year", "2.5%", "97.5%"]]
             .rename(columns={"design": "Null design", "outcome": "Outcome (log units)", "fake_year": "Fake adoption"})),
          "",
          "**Why the MDE may be optimistic.** ACAG PM2.5 is a smooth, calibrated product and the estimate averages over "
          "a hundred units, so pre-period noise is small. But (1) the placebo designs have 4-5 pre-years and 4-5 "
          "post-years, while the real design has 9 pre-years and post-years reaching 6 years after adoption (2019, "
          "2021-2024), where synthetic controls drift more; (2) the placebo assigns all units at once, while the real "
          "estimator averages per-cohort SDIDs (the 2021 cohort alone is small); (3) even region-matched sets are more "
          "dispersed within regions than the real treated set; (4) the post-2019 period contains shocks the pre-period "
          "does not (COVID, BS-VI). Read the MDE as a lower bound on what the real design can detect.", ""]  # fmt: skip

    L += ["## 5. Pre-period placebo on the real NCAP units", "",
          "The same estimator with the actual treated units and fake adoption years, still on data up to 2018. SE and "
          f"the equal-tailed permutation p-value come from the {DESIGNS[ACTUAL_NULL]} null draws in §4. A CI that excludes 0 would "
          "mean NCAP units were already diverging from their synthetic controls before NCAP.", "",
          V["table_placebo_actual"].strip(), ""]  # fmt: skip

    L += ["## 6. Ground PM10: is a minimum detectable effect meaningful?", "",
          "Valid PM10 station-years (primary completeness rule) before NCAP, by whether the station's urban centre holds "
          "an NCAP city:", "",
          V["table_ground"].strip(), "",
          f"Stations valid in both {int(meta.last_year) - 1} and {int(meta.last_year)}: {V['pm10_pair_stations']} "
          f"(in {V['pm10_pair_units']} NCAP units); non-NCAP: {V['pm10_pair_non']}.", "",
          "**Verdict: no.** An MDE needs an estimate of how much the treated-minus-control change varies when there is "
          f"no effect. Non-NCAP centres have {V['pm10_2017_non']} valid PM10 station-years before 2018, so there is no "
          f"pre-period change at all on the control side, and a placebo DiD cannot be formed. For a within-city "
          f"interrupted time series, only {V['pm10_pair_stations']} stations in {V['pm10_pair_units']} cities give even "
          "one year-to-year change before NCAP: any variance estimate from one year-pair in a handful of cities would "
          "be a number, not an MDE. Ground PM10 results are therefore reported without an MDE and labelled as unable "
          "to test parallel trends (analysis plan §1).", ""]  # fmt: skip

    L += ["## 7. Calibration leakage: which NCAP units gained a monitor", "",
          "ACAG calibrates its satellite estimates to ground monitors, and NCAP added monitors mainly in "
          "NCAP cities, so part of any Layer A effect could reflect calibration rather than air (analysis plan §5). "
          "A treated unit counts as having gained a monitor if a CAAQMS station inside its polygon first reported PM "
          f"in {V['leak_from']}-{V['leak_to']} (the satellite post-period). This uses only the year each station first "
          "reported, no pollution values. The CPCB network is a proxy for the monitors ACAG actually used.", "",
          md(pd.DataFrame({"Group": ["Gained a monitor", "Did not gain one",
                                     f"... of which had a station before {V['leak_from']}",
                                     "... of which never had a station inside the polygon"],
                           "Treated units": [V["leak_gain"], V["leak_nogain"], V["leak_nogain_had"],
                                             V["leak_nogain_never"]]})),
          "", f"Minimum group size to estimate: {V['leak_min']} units. Result: {V['leak_estimable']}.", ""]  # fmt: skip
    return "\n".join(L)


def main(argv: list[str]) -> None:
    D = load()
    cmd = argv[0] if argv else "report"
    if cmd == "report":
        REPORT.write_text(build(D), encoding="utf-8")
        print(f"wrote {REPORT}")
    elif cmd == "sync-plan":
        V = plan_values(D)
        for f in PLAN_FILES:
            f.write_text(fill(f.read_text(encoding="utf-8"), V), encoding="utf-8")
            print(f"synced {f}")
    elif cmd == "check-plan":
        V = plan_values(D)
        bad = {f.name: stale(f.read_text(encoding="utf-8"), V) for f in PLAN_FILES}
        bad = {k: v for k, v in bad.items() if v}
        if bad:
            sys.exit(f"stale pre-gate numbers: {bad}. Run sync-plan and log a deviation.")
        print("analysis plan numbers match the pipeline")
    else:
        sys.exit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
