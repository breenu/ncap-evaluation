"""The pre-set lockdown smear test (DEC-119): does a lockdown indicator change 2019/2021 deweathered
annual means by more than the threshold on the pilot stations?

For the 40 pilot series, compares the full-run `gam` fits with `gam_lock` fits (same inputs, same
draws; plus a 0/1 term for the national lockdown days). Station-years valid under the primary rule
(primary completeness variant, near-constant station-years excluded), primary seasonal scheme,
annual means over the same valid days: |dw_gam_lock / dw_gam - 1| in %. The decision metric is the
median over 2019 and 2021 pooled (both pollutants); 2019, 2021 and 2020 are also shown separately.

    python -m src.normalise.lockdown_test   -> data/processed/deweathered/lockdown_test.csv, .json
"""

import json
import math

import pandas as pd

from src.common.paths import PROCESSED, params
from src.normalise import collect
from src.normalise.aggregate import OUT, near_constant, scheme_columns
from src.normalise.features import cfg
from src.normalise.pilot import STATIONS_CSV
from src.normalise.store import task_paths


def station_years(fam: str, pollutant: str, sid: str) -> pd.DataFrame:
    out, js = collect.load("main", fam, pollutant, sid)
    col = next(k for k, v in scheme_columns("main").items() if v == "")
    d = collect.deweathered(out, collect.metrics(out)["smear"])[["date", col]].rename(columns={col: fam})
    need = math.ceil(24 * params()["completeness"]["min_hour_share_per_day"])
    day = pd.read_parquet(PROCESSED / "station_day.parquet", columns=["sid", "date_ist", f"{pollutant}_h1"],
                          filters=[("sid", "==", sid)]).rename(columns={"date_ist": "date"})  # fmt: skip
    d = d.merge(day[day[f"{pollutant}_h1"] >= need][["date"]], on="date")
    y = d.assign(year=d.date.dt.year).groupby("year")[fam].mean().reset_index()
    return y.assign(lockdown_term=js.get("lockdown_term"))


def main() -> None:
    c = cfg()
    sids = pd.read_csv(STATIONS_CSV).sid
    q = pd.read_parquet(PROCESSED / "station_year_quality.parquet", columns=["sid", "pollutant", "year", "valid_q1_t75"])
    nc = near_constant()
    rows = []
    for sid in sids:
        for p in ("pm25", "pm10"):
            if not task_paths("main", "gam_lock", p, sid)[1].exists():
                continue
            a = station_years("gam", p, sid).drop(columns="lockdown_term")
            b = station_years("gam_lock", p, sid)
            rows.append(a.merge(b, on="year").assign(sid=sid, pollutant=p))
    t = pd.concat(rows, ignore_index=True)
    t = t.merge(q, on=["sid", "pollutant", "year"], how="left").merge(nc, on=["sid", "pollutant", "year"], how="left")
    t["valid"] = t.valid_q1_t75.fillna(False).astype(bool) & ~t.near_constant.fillna(False).astype(bool)
    t["abs_diff_pct"] = 100 * (t.gam_lock / t.gam - 1).abs()
    v = t[t.valid]
    test = v[v.year.isin([2019, 2021])]
    med = float(test.abs_diff_pct.median())
    res = {
        "series": int(t[["sid", "pollutant"]].drop_duplicates().shape[0]),
        "series_with_lockdown_term": int(t.drop_duplicates(["sid", "pollutant"]).lockdown_term.fillna(False).sum()),
        "station_years_2019_2021": len(test),
        "median_abs_diff_pct_2019_2021": round(med, 3),
        "median_abs_diff_pct_2019": round(float(v[v.year == 2019].abs_diff_pct.median()), 3),
        "median_abs_diff_pct_2021": round(float(v[v.year == 2021].abs_diff_pct.median()), 3),
        "median_abs_diff_pct_2020": round(float(v[v.year == 2020].abs_diff_pct.median()), 3),
        "max_abs_diff_pct_2019_2021": round(float(test.abs_diff_pct.max()), 3),
        "threshold_pct": c["lockdown_test_threshold_pct"],
        "adopt_indicator": bool(med > c["lockdown_test_threshold_pct"]),
    }
    t.to_csv(OUT / "lockdown_test.csv", index=False)
    (OUT / "lockdown_test.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    print(v.groupby("year").abs_diff_pct.describe().round(2))


if __name__ == "__main__":
    main()
