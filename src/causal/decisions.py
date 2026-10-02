"""The registered decision rules of docs/analysis_plan.md §5, read as in DEC-135 and with every branch
fixed in DEC-141 (H1), DEC-140 (H2), DEC-146 (leakage) and DEC-135 (robustness, layer categories).

Pure functions on numbers already estimated; no data is read here. Sign convention (DEC-135): an effect
is treated minus counterfactual on log concentration, so negative = a reduction.
"""

import math

import numpy as np

EQUIV_LO, EQUIV_HI = math.log(0.95), math.log(1.05)  # registered asymmetric bounds (DEC-095/135)


def excludes_zero(lo: float, hi: float) -> bool:
    return lo > 0 or hi < 0


def equivalence(lo90: float, hi90: float, margin_pct: float = 5.0) -> bool:
    """Two one-sided tests at 5%: the 90% CI lies strictly within ln(1 - m) and ln(1 + m)."""
    lo_b, hi_b = math.log(1 - margin_pct / 100), math.log(1 + margin_pct / 100)
    return lo_b < lo90 and hi90 < hi_b


def target_exclusions(lo95: float, hi95: float, targets_pct=(20, 30, 40)) -> dict[int, bool]:
    """Whether the 95% CI excludes a reduction of each target size (DEC-135): lower bound > ln(1 - t)."""
    return {int(t): lo95 > math.log(1 - t / 100) for t in targets_pct}


def h1_verdict(att: float, lo95: float, hi95: float, lo90: float, hi90: float, wald_p: float,
               placebo_lo: float, placebo_hi: float, d_points: dict[str, float],
               wald_p_min: float = 0.10, margin_pct: float = 5.0) -> dict:  # fmt: skip
    """H1 (DEC-141). Rules (a)-(d) and the first-match verdict.

    d_points: point estimates of the rule-(d) specifications (CS, area-weighted, V6.GL.03)."""
    a = att < 0 and hi95 < 0
    b = wald_p > wald_p_min
    c = placebo_lo <= 0 <= placebo_hi
    d_fail = [k for k, v in d_points.items() if not v < 0]
    d = not d_fail
    eq = equivalence(lo90, hi90, margin_pct)
    if not (b and c):
        failed = [x for x, ok in (("(b) pre-trend Wald test", b), ("(c) 2016 placebo", c)) if not ok]
        verdict, code = f"not identified by this design (failed: {', '.join(failed)})", "not_identified"
    elif excludes_zero(lo95, hi95) and att < 0:
        if d:
            verdict, code = "H1 supported", "supported"
        else:
            verdict, code = f"H1 not supported: the sign is not robust ({', '.join(d_fail)} not negative)", "sign_not_robust"
    elif excludes_zero(lo95, hi95) and att > 0:
        verdict, code = "H1 not supported: the estimate is an increase", "increase"
    else:
        tail = ("effects of 5% or larger in either direction are ruled out" if eq else "inconclusive")
        verdict, code = f"no detectable effect; equivalence test: {tail}", "no_detectable_effect"
    return {"a": a, "b": b, "c": c, "d": d, "d_failed": d_fail, "equivalent": eq, "verdict": verdict, "code": code}


def h2_supported(diff_hi95: float) -> bool:
    """H2 (DEC-135/140): winter minus non-winter difference with its 95% CI entirely below 0."""
    return diff_hi95 < 0


def leakage_warning(gained: tuple[float, float, float], notgained: tuple[float, float, float],
                    diff: tuple[float, float, float]) -> tuple[bool, str]:  # fmt: skip
    """DEC-096/146. Each argument is (att, lo95, hi95)."""
    g_att, g_lo, g_hi = gained
    n_att, n_lo, n_hi = notgained
    d_att, d_lo, d_hi = diff
    first = g_att < 0 and g_hi < 0 and n_lo <= 0 <= n_hi
    second = d_att < 0 and d_hi < 0
    reasons = []
    if first:
        reasons.append("the gained group's effect is a reduction with a CI excluding 0 while the not-gained CI includes 0")
    if second:
        reasons.append("the difference (gained minus not gained) is negative with a CI excluding 0")
    return bool(reasons), "; ".join(reasons) if reasons else "no warning sign"


def agrees(primary_att: float, primary_lo95: float, primary_hi95: float, check_att: float) -> bool:
    """Robustness 'agrees' (DEC-135): same sign as the primary and inside the primary's 95% CI."""
    return bool(np.sign(check_att) == np.sign(primary_att) and primary_lo95 <= check_att <= primary_hi95)


def layer_category(a: tuple[float, float, float], b: tuple[float, float, float]) -> str:
    """Layer A vs Layer B (DEC-135), in order, first match wins. Each is (estimate, lo95, hi95)."""
    a_est, a_lo, a_hi = a
    b_est, b_lo, b_hi = b
    if b_lo <= 0 <= b_hi and b_lo <= a_est <= b_hi:
        return "uninformative"
    opposite = np.sign(a_est) != np.sign(b_est)
    if opposite and (excludes_zero(a_lo, a_hi) or excludes_zero(b_lo, b_hi)):
        return "conflict"
    overlap = a_lo <= b_hi and b_lo <= a_hi
    if not opposite and overlap:
        return "consistent"
    if not opposite:
        return "different magnitude"
    return "unclassified"


def pct(log_units: float) -> float:
    """A log-scale effect as a signed % change, 100 (e^b - 1)."""
    return 100 * math.expm1(log_units)


# ---------------------------------------------------------------- Phase 8b: raw MAIAC AOD (DEC-180)
# AOD is a column measure, not surface PM2.5: these rules read direction only. The ACAG estimate on the same
# units enters as a resolution yardstick, as in the registered "uninformative" layer category (DEC-135).

AOD_Q1 = {
    "not_testable": "not testable on this sample (the ACAG rise is not present on these units)",
    "uninformative": "uninformative (the AOD interval contains both 0 and the ACAG estimate)",
    "rise_in_aod": "rise also in AOD",
    "opposite": "opposite direction in AOD",
    "not_reproduced": "rise not reproduced in AOD",
}
AOD_Q2 = {
    "not_testable": "not testable on this sample",
    "uninformative": "uninformative (the AOD interval contains both 0 and the ACAG difference)",
    "gap_reproduced": "gap reproduced in AOD (against calibration leakage)",
    "gap_absent": "gap absent from AOD (consistent with calibration leakage)",
}


def aod_q1(aod: tuple[float, float, float], acag: tuple[float, float, float]) -> dict:
    """Q1 (DEC-180): does the relative rise appear in AOD? Each argument is (estimate, lo95, hi95), same units."""
    a, a_lo, a_hi = aod
    p, p_lo, p_hi = acag
    if not (p > 0 and p_lo > 0):
        code = "not_testable"
    elif a_lo <= 0 <= a_hi and a_lo <= p <= a_hi:
        code = "uninformative"
    elif a > 0 and a_lo > 0:
        code = "rise_in_aod"
    elif a < 0 and a_hi < 0:
        code = "opposite"
    else:
        code = "not_reproduced"
    return {"code": code, "label": AOD_Q1[code]}


def aod_q2(diff_aod: tuple[float, float, float], diff_acag: tuple[float, float, float],
           n_gained: int, n_notgained: int, min_units: int = 10) -> dict:  # fmt: skip
    """Q2 (DEC-180): does the gained-minus-not-gained gap appear in AOD? Differences as (estimate, lo95, hi95)."""
    d, d_lo, d_hi = diff_aod
    p, _p_lo, p_hi = diff_acag
    if min(n_gained, n_notgained) < min_units:
        code, why = "not_testable", f"a group has fewer than {min_units} units"
    elif not (p < 0 and p_hi < 0):
        code, why = "not_testable", "the ACAG difference on these units is not negative with a CI excluding 0"
    elif d_lo <= 0 <= d_hi and d_lo <= p <= d_hi:
        code, why = "uninformative", ""
    elif d < 0 and d_hi < 0:
        code, why = "gap_reproduced", ""
    else:
        code, why = "gap_absent", ""
    return {"code": code, "label": AOD_Q2[code] + (f" ({why})" if why else "")}
