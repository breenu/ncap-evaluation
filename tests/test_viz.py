"""Tests for Phase 9 figures (src/viz/wording.py, style.py, catalogue.py, fig1_decomposition.py; DEC-190 to
DEC-195). SYNTHETIC DATA ONLY: every string, frame and figure below is made up to exercise one rule; none of
it is real air-quality data or a real result."""

import json

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib import pyplot as plt  # noqa: E402

from src.viz import catalogue, style, wording  # noqa: E402

# ------------------------------------------------------------------ wording (DEC-193)


@pytest.mark.parametrize("text", [
    "The policy effect of NCAP",
    "policy-attributable residual",
    "a fall attributable to NCAP",
    "the impact of NCAP on PM2.5",
    "NCAP reduced PM2.5 by 4%",
    "cleaner air due to NCAP",
    "listed minus counterfactual",
    "the best and worst cities",
    "top 10 cities",
    "the effect of NCAP was +3%",
    "Effects of NCAP by region",
])  # fmt: skip
def test_banned_wording_is_caught(text):
    assert wording.problems(text)
    with pytest.raises(ValueError, match="banned wording"):
        wording.check(text, "synthetic")


@pytest.mark.parametrize("text", [
    "Not an effect of NCAP.",
    "These are relative changes, not effects of NCAP.",
    "Not identified as an effect of NCAP: the registered pre-trend test failed.",
    "H1 is not identified by this design (registered pre-trend test failed): not an effect of NCAP.",
    "Nothing here is an effect of NCAP",
    "best-quality QA, all valid months",
    "Relative change against comparison cities (satellite PM2.5)",
])  # fmt: skip
def test_allowed_wording_passes(text):
    assert wording.problems(text) == []


def test_negation_must_be_in_the_same_clause():
    # a negation in an earlier sentence does not excuse a later claim
    assert wording.problems("This is not causal. The effect of NCAP was large.")


def test_each_figure_text_is_checked_on_its_own():
    fig, ax = plt.subplots()
    ax.set_title("Not identified")  # a negation in one label ...
    ax.set_xlabel("effect of NCAP (%)")  # ... cannot excuse another
    with pytest.raises(ValueError):
        wording.check_figure(fig, "synthetic")
    plt.close(fig)


# ------------------------------------------------------------------ style.save (DEC-192/194)


def _fig(title: str = "Synthetic line") -> plt.Figure:
    style.apply()
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [1, 3, 2], label="series")
    ax.set_title(title)
    ax.set_xlabel("x (units)")
    return fig


def test_save_writes_byte_identical_svg_and_png(tmp_path, monkeypatch):
    monkeypatch.setattr(style, "FIGURES", tmp_path)
    meta = style.Meta("T", "Synthetic", "Synthetic question?", "Synthetic caption.", "Synthetic alt text.")
    style.save(_fig(), "a", meta)
    first = {ext: (tmp_path / f"a.{ext}").read_bytes() for ext in ("png", "svg", "json")}
    style.save(_fig(), "a", meta)
    for ext in ("png", "svg", "json"):
        assert (tmp_path / f"a.{ext}").read_bytes() == first[ext], ext
    assert b"<dc:date>" not in first["svg"]
    assert json.loads(first["json"])["alt"] == "Synthetic alt text."


def test_save_refuses_banned_wording_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(style, "FIGURES", tmp_path)
    with pytest.raises(ValueError):
        style.save(_fig("Policy effect by city"), "b")
    assert not list(tmp_path.iterdir())
    meta = style.Meta("T", "ok", "ok?", "The impact of NCAP.", "ok")
    with pytest.raises(ValueError):
        style.save(_fig(), "c", meta)
    assert not list(tmp_path.iterdir())


# ------------------------------------------------------------------ catalogue (DEC-194)


def test_catalogue_lists_every_figure_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue, "FIGURES", tmp_path)
    monkeypatch.setattr(catalogue, "ORDER", ["x2", "x1"])
    for n in ("x1", "x2"):
        (tmp_path / f"{n}.json").write_text(json.dumps({"name": n, "number": n[-1], "title": f"T{n}", "question": "Q?",
                                                        "caption": "C.", "alt": "A."}), encoding="utf-8")  # fmt: skip
    md = catalogue.render(catalogue.load())
    assert md.index("## Figure 2.") < md.index("## Figure 1.")
    assert "../reports/figures/x1.png" in md


def test_catalogue_fails_without_a_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue, "FIGURES", tmp_path)
    monkeypatch.setattr(catalogue, "ORDER", ["missing"])
    with pytest.raises(FileNotFoundError):
        catalogue.load()


def test_catalogue_rechecks_wording(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue, "FIGURES", tmp_path)
    monkeypatch.setattr(catalogue, "ORDER", ["x"])
    (tmp_path / "x.json").write_text(json.dumps({"name": "x", "number": "1", "title": "t", "question": "q",
                                                 "caption": "NCAP worked.", "alt": "a"}), encoding="utf-8")  # fmt: skip
    with pytest.raises(ValueError):
        catalogue.load()


# ------------------------------------------------------------------ figure 1's illustrative cities (DEC-191)


def test_illustrative_cities_rule():
    from src.normalise import composition as C
    from src.viz.fig1_decomposition import illustrative_cities

    rows = [  # unit, stations valid in 2025, panel stations, region
        ("u1", 5, 1, "coastal"), ("u2", 5, 2, "coastal"),  # tie on 2025 count: more panel stations wins -> u2
        ("u3", 40, 20, "igp"), ("u4", 13, 1, "igp"),
        ("u5", 9, 1, "peninsular/other"), ("u6", 7, 1, "peninsular/other"),
        ("u7", 3, 1, "igp"),
    ]  # fmt: skip
    ch = pd.DataFrame([{"unit_id": u, "n_all_end": n, "n_panel": k, "pollutant": "pm25", "spec": C.PRIMARY.label}
                       for u, n, k, _ in rows])  # fmt: skip
    ch = pd.concat([ch, ch.assign(pollutant="pm10", n_all_end=99)])  # PM10 counts must not matter
    regions = pd.Series({u: r for u, _, _, r in rows})
    picks = illustrative_cities(ch, regions, n=4)
    assert picks[:3] == ["u2", "u3", "u5"]  # one per region, regions in name order
    assert picks[3] == "u4"  # then the most stations not yet chosen
    with pytest.raises(ValueError):
        illustrative_cities(ch, regions.drop("u7"), n=4)
