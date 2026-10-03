"""Phase 10 documents (DEC-206): no hand-typed result numbers, every variable exists, the wording rules hold,
and every logged deviation is in Appendix A. The first tests use SYNTHETIC strings; the last ones check the
committed report sources, so CI checks them too."""

import pytest

from src.report import check as K


@pytest.mark.parametrize("text", ["The estimate is +3.6% (95% CI +2.4% to +4.8%).", "H4 is 9.5 pp.", "113 units", "p = 0.0008"])
def test_typed_numbers_are_caught(text):
    assert K.typed_numbers(text)


@pytest.mark.parametrize("text", [
    "The estimate is {{< var causal.att >}} (95% CI {{< var causal.ci >}}).",
    "From 2018 to 2025, and 2010–2024.", "See Figure 4, Table 6, Figures 5 and 6, §4 and Appendix A.",
    "H1, H5, RQ2, PM2.5, PM10, V5.GL.06, DEC-135 and commit `6e24eca`.", "Registered on 27 September 2026.",
    "Ended in 2019.", "1. First item",
])  # fmt: skip
def test_allowed_numbers_pass(text):
    assert K.typed_numbers(text) == []


def test_missing_variable_is_caught():
    V = {"causal": {"att": "+3.6%"}}
    assert K.missing_variables("{{< var causal.att >}} and {{< var causal.nope >}}", V) == ["causal.nope"]


def test_result_like_numbers_in_includes():
    assert K.RESULT_LIKE.findall("a fall of −23.6% and +9.5 pp")
    assert not K.RESULT_LIKE.findall("completeness 90% as a sensitivity; 2015–2025; 500 draws")


# ---------------------------------------------------------------- the committed documents


def test_committed_documents_pass_every_check():
    bad = {k: v for k, v in K.all_problems().items() if v}
    assert bad == {}


def test_every_deviation_is_listed():
    logged = K.logged_deviations()
    assert {"DEC-109", "DEC-110", "DEC-116"} <= logged  # the three registered-plan deviations
    assert logged <= K.listed_in_appendix()
