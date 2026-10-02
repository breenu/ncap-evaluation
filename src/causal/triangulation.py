"""Triangulation between Layer A and Layer B, and the registered investigation (plan §5; DEC-135, DEC-150).
Phase 7 Part B. GATED (hard rule 4).

Pairs (PM2.5 only, never averaged): Layer A restricted to the units with a Layer B PM2.5 panel, against
the ground DiD (the like-for-like pair) and against the ITS. Each pair gets DEC-135's ordered category.
Every pair not classified "consistent" triggers the four registered investigation steps, each reported
whether or not it closes the gap:
    1 network composition   Layer B on the all-station city series instead of the panel
    2 calibration           Layer A restricted on V6.GL.02.04 (to 2023) vs V5.GL.06; the yearly correlation
                            across these cities between ground panel means and the satellite
    3 spatial coverage      ITS of the satellite at the panel stations' own cells vs the polygon value
    4 deweathering          Layer B on raw vs deweathered values

    python -m src.causal.triangulation    -> data/processed/causal/triangulation.csv, investigation.csv
"""

import numpy as np
import pandas as pd

from src.causal import decisions as D
from src.causal import layer_a as A
from src.causal import layer_b as B
from src.causal import report_maiac as RM
from src.common.gate import require_gate
from src.normalise import composition as C


def layer_b_row(est: pd.DataFrame, version: str, estimator: str, pol: str = "pm25") -> pd.Series:
    r = est[(est.version == version) & (est.estimator == estimator) & (est.pollutant == pol)]
    if len(r) != 1:
        raise ValueError(f"Layer B {version}/{estimator}/{pol}: {len(r)} rows")
    return r.iloc[0]


def pairs(sdid: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    a = sdid.set_index(["spec_id", "estimand"]).loc[("restricted_pm25", "att")]
    rows = []
    for name, estimator in (("ground DiD (like-for-like)", "DiD"), ("ITS", "ITS")):
        b = layer_b_row(est, "primary", estimator)
        cat = D.layer_category((a.att, a.lo95, a.hi95), (b.est, b.lo95, b.hi95))
        rows.append({"pair": f"Layer A restricted vs {name}", "a_est": a.att, "a_lo95": a.lo95, "a_hi95": a.hi95,
                     "a_units": int(a.n_treated), "b_est": b.est, "b_lo95": b.lo95, "b_hi95": b.hi95,
                     "b_cities": int(b.cities), "category": cat, "investigate": cat != "consistent"})  # fmt: skip
    return pd.DataFrame(rows)


def ground_sat_correlation() -> pd.DataFrame:
    """Per year, across the H4 PM2.5 cities: correlation of log ground panel mean (raw) and log satellite."""
    t = pd.read_parquet(C.OUT / "trends.parquet")
    units = set(A.restricted_units("pm25"))
    # the panel is defined from the baseline year (DEC-125), so the series starts there (DEC-150)
    t = t[(t.pollutant == "pm25") & (t.set == "panel") & t.unit_id.isin(units) & t.sat.notna() & (t.year >= C.PRIMARY.baseline)]
    rows = []
    for y, g in t.groupby("year"):
        rows.append({"year": int(y), "cities": len(g), "corr_log": float(np.corrcoef(np.log(g.raw), np.log(g.sat))[0, 1])})
    return pd.DataFrame(rows)


def investigation(sdid: pd.DataFrame, est: pd.DataFrame, satcell: pd.DataFrame) -> pd.DataFrame:
    s = sdid.set_index(["spec_id", "estimand"])
    rows = []

    def add(step, what, est_, lo, hi, note=""):
        rows.append({"step": step, "quantity": what, "est": est_, "lo95": lo, "hi95": hi, "note": note})

    for estimator in ("ITS", "DiD, city means"):
        for ver, lab in (("primary", "balanced panel, deweathered"), ("all_stations", "all stations, deweathered")):
            r = layer_b_row(est, ver, estimator)
            add(1, f"{estimator}: {lab}", r.est, r.lo95, r.hi95)
    for sid, lab in (("restricted_pm25", "Layer A restricted, V5.GL.06 (2019, 2021-2024)"),
                     ("restricted_pm25_v6gl0204", "Layer A restricted, V6.GL.02.04 vintage (2019, 2021-2023)")):  # fmt: skip
        r = s.loc[(sid, "att")]
        add(2, lab, r.att, r.lo95, r.hi95)
    if RM.have() and (row := RM.investigation_row()):  # Phase 8b: raw AOD, direction only (DEC-181)
        add(row["step"], row["quantity"], row["est"], row["lo95"], row["hi95"], row["note"])
    for r in ground_sat_correlation().itertuples():
        add(2, f"correlation of log ground panel and log satellite across {r.cities} cities, {r.year}", r.corr_log, np.nan, np.nan)
    for r in satcell.itertuples():
        add(3, f"ITS 2018 -> 2024: {r.series} ({r.cities} cities)", r.est, r.lo95, r.hi95)
    for estimator in ("ITS", "DiD"):
        for ver, lab in (("primary", "deweathered"), ("raw", "raw")):
            r = layer_b_row(est, ver, estimator)
            add(4, f"{estimator}: {lab}", r.est, r.lo95, r.hi95)
    return pd.DataFrame(rows)


def main() -> None:
    require_gate("Triangulation of Layer A and Layer B")
    sdid = pd.read_csv(A.OUT / "sdid_summary.csv")
    est = pd.read_csv(B.OUT / "estimates.csv")
    satcell = pd.read_csv(B.OUT / "satellite_at_stations.csv")
    p = pairs(sdid, est)
    p.to_csv(A.OUT / "triangulation.csv", index=False)
    investigation(sdid, est, satcell).assign(triggered=bool(p.investigate.any())).to_csv(A.OUT / "investigation.csv", index=False)
    print(p[["pair", "category"]].to_string(index=False))


if __name__ == "__main__":
    main()
