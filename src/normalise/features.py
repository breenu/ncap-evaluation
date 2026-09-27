"""Model inputs for deweathering, one folder per station and pollutant (Phase 5, DEC-100 to DEC-102).

For station s and pollutant p (PM2.5, PM10), with the ERA5 cell holding the station, under
data/interim/normalise/inputs/<run>/<pollutant>/<sid>/ (run = pilot or main):
    fit.parquet     valid days (>= 18 of 24 valid hours, the primary rule) to fit_end:
                    date, t_row (its row in target), y = log daily mean, weather, doy, weekday,
                    trend, year
    target.parquet  every day with any data to fit_end (so the 60/90% and 3-of-4-hour variants can
                    be averaged later): date, doy, weekday, trend. The deweathered value of a day
                    needs only its date: the weather is resampled.
    pool.parquet    the weather pool: ERA5 days at the cell over weather_pool_years (complete days)
    idx_<scheme>.parquet   resample indices into pool rows, one uint16 column `idx`, target-major
                    (row t * n + k is draw k for target t). Written once and read by BOTH model
                    families, so LightGBM and the GAM normalise with identical weather draws.
    folds.parquet   the CV test years (column `year`), also read by both families.
    wfolds.parquet  within-period blocked CV (DEC-112): `wfold` (1..K) per fit row, and one training
                    mask per fold (`w1`..`wK`): a held-out month and the days within the buffer of
                    it are left out of that fold's training.
Runs (DEC-110): `main` leaves the days of near-constant station-years out of the fit (the primary
analysis); `registered` refits, with every day the registered flags keep, only the series that have
such station-years (the sensitivity analysis).
Both families write their predictions in target row order (src.normalise.store).

trend = years since 2015-01-01; doy = day of year (1-366); weekday = 0 (Monday) to 6.

Forward-chaining folds by calendar year: test year Y is used if the years before Y hold at least
cv_min_train_days fit days and Y at least cv_min_test_days. Training never sees Y or later.
"""

import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.acquire.stations import snap_to_grid
from src.common.paths import INTERIM, PROCESSED, params
from src.normalise.era5_daily import FEATURES, cell_id

INPUTS = INTERIM / "normalise" / "inputs"
POLLUTANTS = ("pm25", "pm10")
TREND_ORIGIN = pd.Timestamp("2015-01-01")


def cfg() -> dict:
    return params()["deweathering"]


def valid_day_hours() -> int:
    """Hours a valid day needs under the primary completeness rule (ceil(24 x 0.75) = 18)."""
    return int(np.ceil(24 * params()["completeness"]["min_hour_share_per_day"]))


def time_features(dates: pd.Series) -> pd.DataFrame:
    d = pd.to_datetime(dates)
    return pd.DataFrame(
        {
            "doy": d.dt.dayofyear.astype("int16"),
            "weekday": d.dt.weekday.astype("int8"),
            "trend": ((d - TREND_ORIGIN).dt.days / 365.25).astype("float64"),
        },
        index=dates.index,
    )


def station_cells(stations: pd.DataFrame) -> pd.Series:
    """sid -> ERA5 cell id; stations with no coordinate at all are absent."""
    s = stations.dropna(subset=["lat", "lon"])
    return pd.Series(
        [cell_id(snap_to_grid(a), snap_to_grid(b)) for a, b in zip(s.lat, s.lon)], index=s.sid
    )


def forward_folds(years: pd.Series, min_train: int, min_test: int) -> list[int]:
    """Test years for blocked forward-chaining CV: all earlier years train, the year itself tests."""
    counts = years.value_counts().sort_index()
    folds = []
    for y, n in counts.items():
        if n >= min_test and counts[counts.index < y].sum() >= min_train:
            folds.append(int(y))
    return folds


def within_folds(dates: pd.Series, k: int, buffer: int) -> tuple[np.ndarray, np.ndarray]:
    """Within-period blocked CV: calendar months dealt round-robin into k folds (consecutive months
    fall in different folds). Returns the fold of each day and a (days, k) training mask that is
    False for the fold's test days and for every day within `buffer` days of one."""
    ym = pd.to_datetime(dates).dt.to_period("M")
    order = {m: i % k + 1 for i, m in enumerate(sorted(ym.unique()))}
    fold = ym.map(order).to_numpy().astype("int16")
    day = pd.to_datetime(dates).to_numpy().astype("datetime64[D]").astype(np.int64)
    train = np.ones((len(day), k), dtype=bool)
    for f in range(1, k + 1):
        test = np.sort(day[fold == f])
        if len(test) == 0:
            continue
        i = np.searchsorted(test, day)  # nearest test day is test[i] or test[i - 1]
        right = test[np.minimum(i, len(test) - 1)]
        left = test[np.maximum(i - 1, 0)]
        near = np.minimum(np.abs(day - right), np.abs(day - left))
        train[:, f - 1] = near > buffer
    return fold, train


def doy_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular distance in days between days of year (a year of 365.25 days)."""
    d = np.abs(a.astype(float) - b.astype(float)) % 365.25
    return np.minimum(d, 365.25 - d)


def resample_indices(
    target_doy: np.ndarray,
    pool_doy: np.ndarray,
    n: int,
    scheme: str,
    window: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """(len(target), n) indices into the pool, drawn with replacement.

    seasonal: from pool days within +-window days of year of the target day (any year);
    annual:   from any pool day (Grange & Carslaw's default)."""
    out = np.empty((len(target_doy), n), dtype=np.uint16)
    if len(pool_doy) >= 2**16:
        raise ValueError("pool too large for uint16 indices")
    if scheme == "annual":
        out[:] = rng.integers(0, len(pool_doy), size=out.shape)
        return out
    if scheme != "seasonal":
        raise ValueError(f"unknown resample scheme {scheme!r}")
    for doy in np.unique(target_doy):
        cand = np.flatnonzero(doy_distance(pool_doy, np.array(doy)) <= window)
        rows = np.flatnonzero(target_doy == doy)
        out[rows] = cand[rng.integers(0, len(cand), size=(len(rows), n))]
    return out


def rng_for(sid: str, pollutant: str, scheme: str) -> np.random.Generator:
    """Deterministic per series: the same seed gives the same draws on any machine and worker count."""
    key = zlib.crc32(f"{sid}|{pollutant}|{scheme}".encode())
    return np.random.default_rng([params()["seed"], key])


def series_dir(run: str, pollutant: str, sid: str) -> Path:
    return INPUTS / run / pollutant / sid


def build_series(
    run: str,
    day: pd.DataFrame,
    weather: pd.DataFrame,
    pollutant: str,
    n: int,
    schemes: list[str],
    exclude_years: frozenset[int] = frozenset(),
) -> dict | None:
    """Write the input folder of one station-pollutant. `day` is that station's station-day rows,
    `weather` the ERA5 days of its cell; days of `exclude_years` are left out of the fit (they stay
    targets). Returns a summary row, or None if too few valid days."""
    c = cfg()
    end = pd.Timestamp(c["fit_end"])
    y0, y1 = c["weather_pool_years"]
    sid = day.sid.iloc[0]
    day = day[(day.date <= end) & (day[f"{pollutant}_h1"] > 0) & (day[pollutant] > 0)]
    fit = day[day[f"{pollutant}_h1"] >= valid_day_hours()]
    fit = fit.merge(weather, on="date", how="inner")  # drops only the window's first Indian day
    fit = fit[~fit.date.dt.year.isin(exclude_years)].reset_index(drop=True)
    if len(fit) < c["min_fit_days"]:
        return None
    fit = pd.concat(
        [
            pd.DataFrame({"date": fit.date, "y": np.log(fit[pollutant])}),
            fit[FEATURES],
            time_features(fit.date),
        ],
        axis=1,
    ).assign(year=lambda f: f.date.dt.year.astype("int16"))
    target = day[["date"]].reset_index(drop=True)
    target = pd.concat([target, time_features(target.date)], axis=1)
    rows = pd.Series(target.index, index=target.date)
    fit.insert(1, "t_row", rows.loc[fit.date].to_numpy().astype("int32"))
    pool = weather[weather.date.dt.year.between(y0, y1)].reset_index(drop=True)
    pool = pd.concat([pool, time_features(pool.date).drop(columns="trend")], axis=1)

    d = series_dir(run, pollutant, sid)
    d.mkdir(parents=True, exist_ok=True)
    fit.to_parquet(d / "fit.parquet", index=False)
    target.to_parquet(d / "target.parquet", index=False)
    pool.to_parquet(d / "pool.parquet", index=False)
    for scheme in schemes:
        idx = resample_indices(
            target.doy.to_numpy(), pool.doy.to_numpy(), n, scheme, c["resample_window_days"],
            rng_for(sid, pollutant, scheme),
        )  # fmt: skip
        pd.DataFrame({"idx": idx.ravel()}).to_parquet(d / f"idx_{scheme}.parquet", index=False)
    folds = forward_folds(fit.year, c["cv_min_train_days"], c["cv_min_test_days"])
    pd.DataFrame({"year": pd.Series(folds, dtype="int16")}).to_parquet(d / "folds.parquet", index=False)
    wf, wt = within_folds(fit.date, c["cv_within_folds"], c["cv_within_buffer_days"])
    w = pd.DataFrame(wt, columns=[f"w{i + 1}" for i in range(wt.shape[1])]).assign(wfold=wf)
    w.to_parquet(d / "wfolds.parquet", index=False)
    return {
        "sid": sid, "pollutant": pollutant, "n_fit": len(fit), "n_target": len(target),
        "first_year": int(fit.year.min()), "last_year": int(fit.year.max()),
        "n_folds": len(folds), "folds": " ".join(map(str, folds)), "n_resamples": n,
        "excluded_years": " ".join(map(str, sorted(exclude_years))),
    }  # fmt: skip


def load_station_day(sids: list[str] | None = None) -> pd.DataFrame:
    cols = ["sid", "date_ist"] + [f"{p}{s}" for p in POLLUTANTS for s in ("", "_h1")]
    filt = [("sid", "in", sids)] if sids else None
    day = pd.read_parquet(PROCESSED / "station_day.parquet", columns=cols, filters=filt)
    return day.rename(columns={"date_ist": "date"})


def near_constant_years() -> dict[tuple[str, str], frozenset[int]]:
    """(sid, pollutant) -> years flagged near-constant (src/clean/nearconstant.py, DEC-110)."""
    y = pd.read_parquet(PROCESSED / "station_year_near_constant.parquet")
    y = y[y.near_constant]
    return {k: frozenset(g.year.astype(int)) for k, g in y.groupby(["sid", "pollutant"])}


def prepare(run: str, sids: list[str] | None, n: int, schemes: list[str]) -> pd.DataFrame:
    """Build input folders for the given stations (all if None). Returns one summary row per
    station-pollutant, including those skipped and why. `main` leaves near-constant station-years
    out of the fit; `registered` builds only the series that have any, with nothing left out."""
    nc = near_constant_years()
    if run == "registered":
        sids = sorted({s for s, _ in nc} & set(sids)) if sids else sorted({s for s, _ in nc})
    stations = pd.read_csv(PROCESSED / "stations.csv")
    cells = station_cells(stations)
    weather = pd.read_parquet(INTERIM / "normalise" / "era5_daily.parquet")
    day = load_station_day(sids)
    rows = []
    for sid, g in day.groupby("sid", sort=True):
        for p in POLLUTANTS:
            if g[f"{p}_h1"].max() <= 0 or pd.isna(g[f"{p}_h1"].max()):
                continue
            if run == "registered" and (sid, p) not in nc:
                continue
            excl = nc.get((sid, p), frozenset()) if run == "main" else frozenset()
            if sid not in cells.index:
                rows.append({"sid": sid, "pollutant": p, "skipped": "no coordinate"})
                continue
            w = weather[weather.cell == cells[sid]].drop(columns="cell")
            if w.empty:
                rows.append({"sid": sid, "pollutant": p, "skipped": f"no ERA5 cell {cells[sid]}"})
                continue
            r = build_series(run, g, w, p, n, schemes, excl)
            rows.append(r or {"sid": sid, "pollutant": p, "skipped": "too few valid days"})
    return pd.DataFrame(rows)
