"""Tests for the read-only dashboard (src/dashboard/build.py; DEC-198 to DEC-201).

The helper tests use SYNTHETIC inputs only. The site tests read the committed, generated sources in dashboard/
(text only, no data is loaded) and check the rules every page must keep: the wording check, the "not identified"
caveat on every city page, alphabetical order, and every attribution DEC-200 requires."""

import re
from pathlib import Path

import pytest

from src.dashboard.build import display_name, post_years, slug
from src.viz import wording

SITE = Path(__file__).resolve().parents[1] / "dashboard"
PAGES = sorted((SITE / "cities").glob("*.qmd"))
needs_site = pytest.mark.skipif(not PAGES, reason="dashboard sources not built")


def test_slug_and_names():
    assert slug("Delhi, Faridabad, Ghaziabad, Noida") == "delhi-faridabad-ghaziabad-noida"
    assert slug("Asansol & Raniganj") == "asansol-raniganj"
    assert slug("Hubli-Dharwad") == "hubli-dharwad"
    assert display_name("Mumbai;Navi Mumbai;Thane") == "Mumbai, Navi Mumbai, Thane"


def test_post_years_skip_2020():
    assert post_years(2019) == "2019 and 2021–2024"
    assert post_years(2020) == "2021–2024"
    assert post_years(2021) == "2021–2024"


@needs_site
def test_every_page_passes_the_wording_check():
    for p in [*PAGES, SITE / "index.qmd", SITE / "about.qmd", SITE / "_quarto.yml"]:
        wording.check(p.read_text(encoding="utf-8"), str(p.name))


@needs_site
def test_every_city_page_carries_the_caveat():
    for p in PAGES:
        t = p.read_text(encoding="utf-8")
        assert "H1 is not identified by this design" in t, p.name
        assert "Nothing on this page is an effect of NCAP" in t, p.name
        assert "{.callout-important}" in t, p.name


@needs_site
def test_every_city_page_serves_a_wide_and_a_phone_chart():
    for p in PAGES:
        t = p.read_text(encoding="utf-8")
        narrow = re.search(r'<source media="\(max-width: 600px\)" srcset="(img/[^"]+-narrow\.png)">', t)
        wide = re.search(r'<img src="(img/[^"]+\.png)" alt="Four charts for [^"]+"', t)
        assert narrow and wide, p.name
        for rel in (narrow.group(1), wide.group(1)):
            assert (p.parent / rel).exists(), rel


@needs_site
def test_cities_are_listed_alphabetically_and_never_ranked():
    idx = (SITE / "index.qmd").read_text(encoding="utf-8")
    listed = re.findall(r"^- \[(.+?)\]\(cities/", idx, flags=re.M)
    assert len(listed) == len(PAGES)
    assert listed == sorted(listed, key=str.lower)
    options = re.findall(r'<option value="cities/[^"]+">(.+?)</option>', idx)
    assert options == listed
    for p in PAGES:
        text = p.read_text(encoding="utf-8").replace("cities cannot be ranked", "")  # the one allowed, negated use
        assert not re.search(r"\brank", text, flags=re.I), p.name


@needs_site
def test_about_page_has_every_required_attribution():
    a = (SITE / "about.qmd").read_text(encoding="utf-8")
    for needed in ["india-cpcb-aqi", "Open Database License (ODbL) 1.0", "made available under the ODbL 1.0",
                   "Contains modified Copernicus Climate Change Service information", "10.24381/1cf1ad76",
                   "10.24381/cds.f17050d7", "10.1002/qj.3803", "10.1021/acs.est.1c05309", "10.1016/j.rse.2023.113624",
                   "10.5194/gmd-18-6767-2025", "© European Union", "10.2905/JRC.05RDPR0",
                   "10.5067/MODIS/MCD19A2.061", "OpenAQ", "DataMeet", "https://osf.io/jksne/",
                   "https://github.com/breenu/ncap-evaluation"]:  # fmt: skip
        assert needed in a, needed
