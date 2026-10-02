"""Funding dose-response on XV Finance Commission ALLOCATIONS. EXPLORATORY (plan §5; DEC-166; cut item 1).
GATED (hard rule 4).

Dose = (FY2020-21 + FY2021-26 air-quality allocation, Rs crore) / UA population (Annex 7.6, millions),
reported in Rs per person. Allocations, not releases: XV-FC releases reward cities that improved
(reverse causality). Per-person allocations are set largely state by state, so the dose is confounded
with state and region. H1 is not identified (DEC-151): this relates **city-level relative changes**, not
effects of NCAP, to money.

    python -m src.hierarchical.dose     -> data/processed/hierarchical/dose_*.csv
"""

import numpy as np
import pandas as pd

from src.causal import layer_a as A
from src.common.gate import require_gate
from src.common.paths import INTERIM, params
from src.hierarchical import pooling as PL
from src.hierarchical.city_estimates import OUT

A2021 = "xvfc_2021_26_vol2_annex_7_6"
A2020 = "xvfc_2020_21_annex_5_3"
RS_PER_PERSON = 10.0  # Rs crore per million people = Rs 10 per person


def ua_allocations(funding: pd.DataFrame) -> pd.DataFrame:
    """One row per XV-FC UA matched to an NCAP city: allocations, population, Rs per person."""
    f = funding[(funding.level == "ua") & funding.cities.notna()]
    a = f[(f.source_doc == A2020) & (f.measure == "allocated_air_quality_2020_21")].groupby("cities").value.sum()
    b = f[(f.source_doc == A2021) & (f.measure == "allocated_air_quality_2021_26")].groupby("cities").value.sum()
    pop = f[(f.source_doc == A2021) & (f.measure == "population_millions")].groupby("cities").value.sum()
    st = f[f.source_doc == A2021].groupby("cities").state_raw.first()
    out = pd.DataFrame({"alloc_2020_21": a, "alloc_2021_26": b, "pop_millions": pop, "state": st}).dropna(
        subset=["alloc_2020_21", "alloc_2021_26", "pop_millions"])
    out["alloc_total"] = out.alloc_2020_21 + out.alloc_2021_26
    out["rs_per_person"] = out.alloc_total / out.pop_millions * RS_PER_PERSON
    return out.rename_axis("city").reset_index()


def unit_dose(units: pd.DataFrame, cities: pd.DataFrame, ua: pd.DataFrame) -> pd.DataFrame:
    """DEC-166: treated units whose NCAP cities are all XV-FC and match >= 1 UA row; Σ alloc / Σ pop."""
    chan = dict(zip(cities.city, cities.channel, strict=True))
    by_city = ua.set_index("city")
    rows = []
    for u in units.itertuples():
        members = [m for m in str(u.ncap_cities).split(";") if m]
        all_xvfc = all(chan.get(m) == "XVFC" for m in members)
        matched = [m for m in members if m in by_city.index]
        reason = ("" if all_xvfc and matched else
                  "a member city is in the NCAP channel" if not all_xvfc else "no allocation row of its own")  # fmt: skip
        r = {"unit_id": u.unit_id, "ncap_cities": u.ncap_cities, "region": u.region, "all_xvfc": all_xvfc,
             "matched": ";".join(matched), "excluded": reason}  # fmt: skip
        if all_xvfc and matched:
            m = by_city.loc[matched]
            r |= {"alloc_total": m.alloc_total.sum(), "pop_millions": m.pop_millions.sum(), "state": ";".join(sorted(set(m.state)))}
            r["rs_per_person"] = r["alloc_total"] / r["pop_millions"] * RS_PER_PERSON
        if all_xvfc or any(chan.get(m) == "XVFC" for m in members):
            rows.append(r)
    return pd.DataFrame(rows)


def within_state(ua: pd.DataFrame) -> pd.DataFrame:
    """How much per-person allocations vary inside a state vs between states (DEC-166 caveat)."""
    g = ua.groupby("state").rs_per_person.agg(["count", "min", "max", "mean"]).reset_index()
    g["range_pct_of_mean"] = 100 * (g["max"] - g["min"]) / g["mean"]
    return g.sort_values("mean")


def main() -> None:
    require_gate("funding dose-response on city-level estimates (exploratory)")
    funding = pd.read_csv(INTERIM / "ncap_funding_clean.csv")
    cities = pd.read_csv(INTERIM / "ncap_cities.csv")
    units = pd.read_csv(A.OUT / "design_units.csv")
    units = units[units.role_a == "treated"]
    ua = ua_allocations(funding)
    ud = unit_dose(units, cities, ua)
    ua.to_csv(OUT / "dose_ua.csv", index=False)
    within_state(ua).to_csv(OUT / "dose_within_state.csv", index=False)
    ud.to_csv(OUT / "dose_units.csv", index=False)
    e = pd.read_csv(OUT / "city_estimates.csv").merge(ud[ud.excluded == ""][["unit_id", "rs_per_person"]], on="unit_id")
    e["log_dose_c"] = np.log(e.rs_per_person) - np.log(e.rs_per_person).mean()
    drop = params()["hierarchical"]["dose_drop_highest"]
    top = e.loc[e.rs_per_person.idxmax()]
    if drop not in str(top.ncap_cities).split(";"):
        raise ValueError(f"highest-dose unit is {top.ncap_cities}, not {drop} as DEC-166 assumed")
    seed = int(params()["seed"])
    specs = [("dose", "log dose", e, ["log_dose_c"]),
             ("dose_igp", "log dose + IGP", e, ["log_dose_c", "igp"]),
             ("dose_no_top", f"log dose, without the highest-dose unit ({drop})", e[e.unit_id != top.unit_id], ["log_dose_c"])]  # fmt: skip
    coefs, diags = [], []
    for key, label, d, X in specs:
        d = d.assign(log_dose_c=np.log(d.rs_per_person) - np.log(d.rs_per_person).mean())
        idata, dg = PL.fit_checked(d.est, d.se, d[X].to_numpy(float), 1.0, seed)
        diags.append({"version": key, "label": label, "units": len(d), **dg})
        if not dg["converged"]:
            continue
        for r in PL.coef_rows(idata, X, key):
            if r["param"] == "beta[log_dose_c]":  # per doubling of the dose
                coefs.append({**r, "param": "per doubling of dose", **{k: r[k] * np.log(2) for k in ("mean", "sd", "lo95", "hi95")}, "units": len(d), "label": label})
            coefs.append({**r, "units": len(d), "label": label})
        print(key, dg, flush=True)
    pd.DataFrame(coefs).to_csv(OUT / "dose_coefs.csv", index=False)
    pd.DataFrame(diags).to_csv(OUT / "dose_diagnostics.csv", index=False)


if __name__ == "__main__":
    main()
