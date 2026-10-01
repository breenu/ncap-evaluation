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
