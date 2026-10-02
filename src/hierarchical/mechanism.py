"""H3, the PM10 vs PM2.5 mechanism test, decided exactly by its registered rule (plan §5; DEC-135, DEC-150,
DEC-165). Layer B (ground): secondary, one pre-year. GATED (hard rule 4).

    (i)   the effect on log(PM2.5/PM10) > 0 with its 95% CI above 0 (co-located stations of both strict
          2018 panels, deweathered), for both the ITS and the DiD;
    (ii)  in >= 2 of 3 specifications (raw = all stations raw; deweathered = all stations deweathered;
          balanced panel = Layer B primary): beta_PM10 < beta_PM2.5 and beta_PM10 < 0, on the cities with
          both pollutants, for both estimators;
    (iii) neither triangulation pair of Phase 7 is "conflict" (DEC-150). Already known to fail (DEC-159),
          so H3 is "inconclusive" whatever (i) and (ii) show (DEC-165).
"consistent with dust control" only if all hold; otherwise "inconclusive"; never "confirmed".

    python -m src.hierarchical.mechanism    -> data/processed/hierarchical/h3_*.csv, h3.json
"""

import json

import numpy as np
import pandas as pd

from src.causal import layer_a as A
from src.causal import layer_b as L
from src.common.gate import require_gate
from src.common.paths import params
from src.hierarchical.city_estimates import OUT

SPECS = [("raw", "all_stations_raw"), ("deweathered", "all_stations"), ("balanced panel", "primary")]  # DEC-165


def common_units(st: pd.DataFrame) -> set:
    """Units holding both pollutants in this series (treated and control alike)."""
    n = st.groupby("unit_id").pollutant.nunique()
    return set(n.index[n == 2])


def its(frame: pd.DataFrame, base: int, label: str, draws: int) -> dict:
    cs = L.city_series(frame)
    d = L.its_city(cs, base)
    lo, hi, se = L.ci(L.boot_its(d, draws, L._rng(label)))
    return {"estimator": "ITS", "est": float(d.d.mean()), "lo95": lo, "hi95": hi, "se": se, "cities": len(d)}


def did(frame: pd.DataFrame, base: int, level: str, label: str, draws: int) -> dict:
    """DiD on stations (level 'stations') or on city means (level 'city means'), as Phase 7 (DEC-148)."""
    if level == "city means":
        frame, key = L.city_series(frame), "unit_id"
    else:
        key = "sid"
    if not L.balanced(frame, key):
        raise ValueError(f"{label}: panel not balanced")
    parts = L.did_parts(frame, key, base)
    emap = L.entity_city(frame, key)
    units_t = {g: emap.reindex(t.index) for g, (t, _) in parts.items()}
    units_c = emap.reindex(next(iter(parts.values()))[1].index)
    est, _ = L.did_estimate(parts, {"t": units_t})
    lo, hi, se = L.ci(L.boot_did(parts, units_t, units_c, draws, L._rng(label)))
    return {"estimator": "DiD", "did_level": level, "est": float(est), "lo95": lo, "hi95": hi, "se": se,
            "cities": int(sum(units_t[g].nunique() for g in parts)), "control_cities": int(units_c.nunique())}  # fmt: skip


def condition_ii(betas: pd.DataFrame) -> pd.DataFrame:
    """Per estimator: in how many specifications beta_PM10 < beta_PM2.5 and beta_PM10 < 0 (DEC-135/165)."""
    w = betas.pivot_table(index=["estimator", "spec"], columns="pollutant", values="est").reset_index()
    w["pm10_fell_more"] = (w.pm10 < w.pm25) & (w.pm10 < 0)
    return w


def ratio_frame(st: pd.DataFrame, value: str) -> pd.DataFrame:
    """Co-located stations of both panels: station-year PM2.5/PM10 of `value` ('y' deweathered, 'raw')."""
    w = st.pivot_table(index=["sid", "unit_id", "year", "group", "cohort"], columns="pollutant", values=value).dropna()
    w = w.reset_index()
    n = w.groupby("sid").year.nunique()
    w = w[w.sid.isin(n.index[n == n.max()])]  # every panel year for both pollutants
    w = w.assign(y=w.pm25 / w.pm10, pollutant="ratio")
    w["raw"] = w["fit"] = w.y  # city_series also averages these; unused for the ratio
    return w[["sid", "unit_id", "pollutant", "year", "group", "cohort", "y", "raw", "fit"]]


def verdict(i_met: bool, ii_met: bool, iii_met: bool) -> str:
    return "consistent with dust control" if (i_met and ii_met and iii_met) else "inconclusive"


def main() -> None:
    require_gate("H3: PM10 vs PM2.5 on the ground layer")
    draws = int(params()["causal"]["ground_bootstrap"])
    sy = L.load_station_years()
    vers = {v.key: v for v in L.versions()}
    rows = []
    for spec, key in SPECS:
        bv = vers[key]
        st = L.station_panel(sy, bv)
        both = common_units(st)
        stc = st[st.unit_id.isin(both)]
        level = "stations" if bv.series == "panel" else "city means"
        for pol in L.POLS:
            f = stc[stc.pollutant == pol]
            base = bv.spec.baseline
            sc = L.scope(f)
            rows.append({"spec": spec, "version": key, "pollutant": pol, "set": "both pollutants",
                         **its(f, base, f"h3|its|{key}|{pol}", draws), **sc})  # fmt: skip
            rows.append({"spec": spec, "version": key, "pollutant": pol, "set": "both pollutants",
                         **did(f, base, level, f"h3|did|{key}|{pol}", draws), **sc})  # fmt: skip
    betas = pd.DataFrame(rows)
    betas.to_csv(OUT / "h3_betas.csv", index=False)
    ii = condition_ii(betas)
    ii.to_csv(OUT / "h3_condition_ii.csv", index=False)
    ii_by_est = ii.groupby("estimator").pm10_fell_more.sum()
    ii_met = bool((ii_by_est >= 2).all() and len(ii_by_est) == 2)

    # (i) the ratio, co-located stations of the primary (balanced) panels
    st = L.station_panel(sy, vers["primary"])
    rrows = []
    for value, lab in (("y", "deweathered"), ("raw", "raw")):
        fr = ratio_frame(st, value)
        sc = L.scope(fr)
        rrows.append({"series": lab, **its(fr, 2018, f"h3|ratio|its|{lab}", draws), **sc})
        rrows.append({"series": lab, **did(fr, 2018, "stations", f"h3|ratio|did|{lab}", draws), **sc})
    ratio = pd.DataFrame(rrows)
    ratio.to_csv(OUT / "h3_ratio.csv", index=False)
    dw = ratio[ratio.series == "deweathered"]
    i_met = bool(((dw.est > 0) & (dw.lo95 > 0)).all() and len(dw) == 2)

    # (iii) Phase 7's triangulation categories (DEC-150)
    tri = pd.read_csv(A.OUT / "triangulation.csv")
    iii_met = bool((tri.category != "conflict").all())
    out = {"i_met": i_met, "ii_met": ii_met, "ii_count": {k: int(v) for k, v in ii_by_est.items()},
           "iii_met": iii_met, "iii_categories": dict(zip(tri.pair, tri.category, strict=True)),
           "verdict": verdict(i_met, ii_met, iii_met)}  # fmt: skip
    (OUT / "h3.json").write_text(json.dumps(out, indent=2))
    print("H3:", out)


if __name__ == "__main__":
    main()
