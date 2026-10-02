"""The registered "VIIRS fire covariate (from 2012)" check (plan §4/§5; DEC-039, DEC-147 item 17, DEC-171).
Phase 7 robustness battery, run on 2026-10-03 after FIRMS was downloaded. GATED (hard rule 4).

    fire_it = log(1 + sum of VIIRS S-NPP FRP (MW) within 100 km of unit i's polygon in year t),
              detections with type 0 (presumed vegetation fire) and confidence nominal/high

The DEC-142 event study (Sun & Abraham; unit and region x year effects; ERA5 covariates; SEs clustered by
unit) with fire added, 2012-2024 without 2020. Comparison number: the average post-period estimate
(l = 0..+5), judged against the primary SDID (DEC-135 "agrees"), as DEC-147 item 13. Reported beside it:
the same event study on 2012-2024 without fire (the window alone), the fire coefficient, the pre-trend Wald
p over the available pre-periods (information only). H1 is not identified (DEC-151): none of this is an
effect of NCAP.

    python -m src.causal.fire covariate    -> data/processed/causal/fire_unit_year.parquet
    python -m src.causal.fire run          -> data/processed/causal/event_study/es_fire*_*
"""

import glob
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from src.causal import event_study as E
from src.causal import layer_a as A
from src.causal.pregate import INDIA_CRS
from src.common.gate import require_gate
from src.common.paths import INTERIM, params, raw_dir

FIRST, LAST = 2012, 2024  # VIIRS S-NPP starts in 2012; Layer A ends in 2024
RADIUS_KM = 100  # DEC-171
KEEP_CONF = {"n", "h"}  # VIIRS confidence: low / nominal / high
OUT = A.OUT / "fire_unit_year.parquet"


def read_year(path: str) -> pd.DataFrame:
    """One FIRMS VIIRS yearly country file, filtered as DEC-171. Stops if the columns are not as documented."""
    d = pd.read_csv(path, usecols=lambda c: c in {"latitude", "longitude", "acq_date", "confidence", "frp", "type"})
    need = {"latitude", "longitude", "acq_date", "confidence", "frp", "type"}
    if need - set(d.columns):
        raise ValueError(f"{path}: missing columns {sorted(need - set(d.columns))} (DEC-171: stop and report)")
    conf = set(d.confidence.astype(str).str.lower().unique())
    if not conf <= {"l", "n", "h"}:
        raise ValueError(f"{path}: unexpected confidence codes {sorted(conf)} (DEC-171: stop and report)")
    if not set(d["type"].unique()) <= {0, 1, 2, 3}:
        raise ValueError(f"{path}: unexpected type codes {sorted(d['type'].unique())} (DEC-171: stop and report)")
    k = (d["type"] == 0) & d.confidence.astype(str).str.lower().isin(KEEP_CONF)
    d = d[k].copy()
    d["year"] = pd.to_datetime(d.acq_date).dt.year
    return d[["latitude", "longitude", "year", "frp"]]


def unit_fire(points: pd.DataFrame, units: gpd.GeoDataFrame, years: range, radius_km: float = RADIUS_KM) -> pd.DataFrame:
    """Sum of FRP within `radius_km` of each unit polygon, per unit-year; 0 where none (every unit x year)."""
    pts = gpd.GeoDataFrame(points, geometry=gpd.points_from_xy(points.longitude, points.latitude), crs=4326).to_crs(INDIA_CRS)
    buf = units[["unit_id", "geometry"]].to_crs(INDIA_CRS)
    buf["geometry"] = buf.geometry.buffer(radius_km * 1000)
    j = gpd.sjoin(pts[["year", "frp", "geometry"]], buf, predicate="within", how="inner")
    s = j.groupby(["unit_id", "year"]).frp.agg(frp_sum="sum", detections="size").reset_index()
    grid = pd.MultiIndex.from_product([units.unit_id, list(years)], names=["unit_id", "year"]).to_frame(index=False)
    out = grid.merge(s, on=["unit_id", "year"], how="left").fillna({"frp_sum": 0.0, "detections": 0})
    out["fire"] = np.log1p(out.frp_sum)
    return out


def covariate() -> None:
    require_gate("fire covariate for the Layer A event study")
    files = sorted(glob.glob(str(raw_dir("firms") / "archive" / "viirs-snpp_*_India.csv")))
    years = range(FIRST, LAST + 1)
    have = {int(f.split("_")[-2]) for f in files}
    if set(years) - have:
        raise FileNotFoundError(f"FIRMS archive years missing: {sorted(set(years) - have)}")
    pts = pd.concat([read_year(f) for f in files if int(f.split("_")[-2]) in years], ignore_index=True)
    pts = pts[pts.year.between(FIRST, LAST)]
    u = pd.read_csv(A.OUT / "design_units.csv")
    u = u[u.role_a.isin(["treated", "control"])]
    g = gpd.read_file(INTERIM / "sat_units.gpkg")
    g = g[g.unit_id.isin(u.unit_id)]
    if len(g) != len(u):
        raise ValueError("a Layer A unit has no polygon")
    out = unit_fire(pts, g, years)
    out.to_parquet(OUT, index=False)
    print(f"fire covariate: {len(pts):,} kept detections; {len(out):,} unit-years; "
          f"share of unit-years with fire within {RADIUS_KM} km: {(out.detections > 0).mean():.3f}")


def run() -> None:
    require_gate("fire-covariate event study (Phase 7 robustness)")
    P = params()["causal"]
    window = tuple(P["event_window"])
    fire = pd.read_parquet(OUT)
    base = E.panel((2020,))
    base = base[base.year.between(FIRST, LAST)].merge(fire[["unit_id", "year", "fire"]], on=["unit_id", "year"], how="left")
    if base.fire.isna().any():
        raise ValueError("fire covariate missing for some unit-years")
    sizes = base[base.cohort > 0].groupby("cohort").unit_id.nunique()
    dd, meta = E.sa_design(base)
    pre, post = list(range(window[0], -1)), list(range(0, window[1] + 1))
    for name, covars in (("es_fire", E.COVARS + ["fire"]), ("es_fire_window", E.COVARS)):
        b, V, f = E.fit(dd, meta, covars)
        t, cov = E.aggregate(b, V, meta, sizes, window)
        res = {"name": name, "years": [FIRST, LAST], "drop_years": [2020], "covariates": covars, "radius_km": RADIUS_KM,
               "n_obs": int(f._N), "n_units": int(base.unit_id.nunique()),
               "references": meta[meta.kind == "ref"][["cohort", "rel"]].to_dict("records"),
               "wald_pre": E.wald(t, cov, pre), "avg_post": E.average(t, cov, post)}  # fmt: skip
        if "fire" in covars:
            res["fire_coef"] = {"coef": float(b["fire"]), "se": float(np.sqrt(V.loc["fire", "fire"]))}
        t.to_csv(E.OUT / f"{name}_coefs.csv", index=False)
        with open(E.OUT / f"{name}_meta.json", "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=float)
        print(name, "avg post", round(res["avg_post"]["coef"], 4), "| Wald pre p", round(res["wald_pre"]["p"], 4),
              "| obs", res["n_obs"])  # fmt: skip


if __name__ == "__main__":
    {"covariate": covariate, "run": run}[sys.argv[1] if len(sys.argv) > 1 else "run"]()
