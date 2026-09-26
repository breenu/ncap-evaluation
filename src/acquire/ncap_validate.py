"""Check the extracted NCAP tables and build the canonical city table.

Inputs: data/interim/ncap_city_lists.csv, ncap_funding.csv, ncap_printed_totals.csv
(from ncap_extract), config/ncap_sources.yaml and config/ncap_city_aliases.yaml.

Outputs:
  data/interim/ncap_cities.csv          one row per NCAP city: list membership over time,
                                        first listing (date added), funding channel, UA
  data/interim/ncap_funding_clean.csv   funding rows with the canonical city attached
  docs/ncap_extraction_mismatches.md    every check that failed, with document and page,
                                        for manual verification (generated; do not edit)

Nothing is corrected automatically. A failed check is listed, not fixed.

    python -m src.acquire.ncap_validate
"""

import re
from collections import defaultdict

import pandas as pd

from src.common.paths import CONFIG, DOCS, INTERIM, load_yaml

MASTER = "cpcb_nac_2022_10"  # CPCB list of 131 cities, 2022-10-10
ROUNDING = 0.015  # crore: differences up to this are treated as rounding in printed totals


def norm(name: str) -> str:
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"\b(u\.?\s?a\.?|urban agglomeration|city)\b", " ", s)
    s = re.sub(r"\((k|gm|hy)\)|\b(k|gm|hy)\b", " ", s)
    return re.sub(r"[^a-z]", "", s)


class Matcher:
    """Printed name -> master city names, using exact normalised matches and the alias file."""

    def __init__(self, master: list[str], alias_cfg: dict):
        self.master = {norm(c): c for c in master}
        self.alias = {norm(k): v for k, v in alias_cfg.get("aliases", {}).items()}
        self.not_ncap = {norm(c) for c in alias_cfg.get("not_ncap", [])}
        self.not_city = {norm(c) for c in alias_cfg.get("not_city", [])}

    def match(self, raw: str) -> tuple[list[str], str]:
        n = norm(raw)
        if n in self.master:
            return [self.master[n]], "exact"
        if n in self.alias:
            return list(self.alias[n]["to"]), self.alias[n]["why"]
        if n in self.not_ncap:
            return [], "not_ncap"
        if n in self.not_city:
            return [], "not_city"
        return [], "unmatched"


def _nums(text: str) -> list[float]:
    return [
        float(x.replace(",", "")) for x in str(text).split() if re.match(r"^\d[\d,]*\.?\d*$", x)
    ]


def run() -> dict:
    sources = {d["id"]: d for d in load_yaml(CONFIG / "ncap_sources.yaml")["documents"]}
    L = pd.read_csv(INTERIM / "ncap_city_lists.csv", keep_default_na=False)
    F = pd.read_csv(INTERIM / "ncap_funding.csv", keep_default_na=False)
    T = pd.read_csv(INTERIM / "ncap_printed_totals.csv", keep_default_na=False)
    F["value"] = pd.to_numeric(F["value"], errors="coerce")
    # Measures printed once per state (merged cells) are not city values: mark them.
    for doc, d in sources.items():
        for i, t in enumerate(d["tables"]):
            for meas in t.get("state_level_measures", []):
                sel = (F.source_doc == doc) & (F.table_idx == i) & (F.measure == meas)
                F.loc[sel, "level"] = "state_merged"
    master_rows = L[L.source_doc == MASTER]
    m = Matcher(list(master_rows.city_raw), load_yaml(CONFIG / "ncap_city_aliases.yaml"))
    issues: dict[str, list[dict]] = defaultdict(list)

    # ---------------------------------------------------------------- lists
    list_docs = [d for d in sources if any(t["kind"] == "city_list" for t in sources[d]["tables"])]
    list_docs.sort(key=lambda d: sources[d]["doc_date"])
    membership: dict[str, dict[str, str]] = defaultdict(dict)  # city -> doc -> printed name
    for doc in list_docs:
        rows = L[L.source_doc == doc]
        spec = next(t for t in sources[doc]["tables"] if t["kind"] == "city_list")
        if spec.get("expected_count") and len(rows) != spec["expected_count"]:
            issues["List counts"].append(
                {
                    "document": doc,
                    "page": ",".join(map(str, spec["pages"])),
                    "detail": f"{len(rows)} entries parsed; title/text says {spec['expected_count']}",
                }
            )
        for r in rows.itertuples():
            cities, how = m.match(r.city_raw)
            if how == "unmatched":
                issues["Names not matched to the master list"].append(
                    {"document": doc, "page": r.page, "detail": f"item {r.item_no}: '{r.city_raw}'"}
                )
            elif how in ("truncated", "combined", "artefact"):
                issues["Names mapped by judgement (check)"].append(
                    {
                        "document": doc,
                        "page": r.page,
                        "detail": f"item {r.item_no}: '{r.city_raw}' -> {', '.join(cities)} ({how})",
                    }
                )
            for c in cities:
                if doc in membership[c]:
                    issues["Duplicate entries within a list"].append(
                        {
                            "document": doc,
                            "page": r.page,
                            "detail": f"{c} appears twice ('{membership[c][doc]}', '{r.city_raw}')",
                        }
                    )
                membership[c][doc] = r.city_raw

    # ---------------------------------------------------------------- funding: names and channel
    F["cities"], F["match"] = zip(*(m.match(c) if c else ([], "") for c in F.city_raw), strict=True)
    city_rows = F[(F.city_raw != "") & (F.level != "state")]
    for (doc, page, raw, how), g in city_rows.groupby(["source_doc", "page", "city_raw", "match"]):
        cities = g.cities.iloc[0]
        if how == "unmatched":
            issues["Names not matched to the master list"].append(
                {"document": doc, "page": page, "detail": f"'{raw}'"}
            )
        elif how in ("truncated", "combined", "artefact"):
            issues["Names mapped by judgement (check)"].append(
                {"document": doc, "page": page, "detail": f"'{raw}' -> {', '.join(cities)} ({how})"}
            )
        elif how == "not_city" and g.value.notna().any():
            vals = "; ".join(f"{r.measure}={r.value_raw}" for r in g.itertuples() if r.measure)
            issues["Rows that are not a single city"].append(
                {"document": doc, "page": page, "detail": f"'{raw}': {vals}"}
            )

    # Channel is a property of each table (one Lok Sabha answer can hold an NCAP and an XV-FC table).
    xvfc_cities = defaultdict(set)
    for r in F[(F.channel == "XVFC") & (F.match != "not_ncap")].itertuples():
        for c in r.cities:
            xvfc_cities[c].add(r.source_doc)

    # ---------------------------------------------------------------- canonical city table
    order = list_docs
    recs = []
    all_cities = sorted(membership, key=lambda c: (c not in set(master_rows.city_raw), c))
    mstate = dict(zip(master_rows.city_raw, master_rows.state_raw, strict=True))
    mstar = dict(zip(master_rows.city_raw, master_rows.marker, strict=True))
    for c in all_cities:
        docs_in = [d for d in order if d in membership[c]]
        first = docs_in[0]
        before = [d for d in order if sources[d]["doc_date"] < sources[first]["doc_date"]]
        rec = {
            "city": c,
            "state": mstate.get(c, ""),
            "in_master_131": c in mstate,
            "million_plus_only": mstar.get(c, "") == "*",
            "first_listed_doc": first,
            "first_listed_date": sources[first]["doc_date"],
            "last_list_without_city": before[-1] if before else "",
            "last_list_without_date": sources[before[-1]]["doc_date"] if before else "",
            "channel": "XVFC" if c in xvfc_cities else "NCAP",
            "xvfc_evidence": ";".join(sorted(xvfc_cities.get(c, []))),
        }
        for d in order:
            rec[f"in_{d}"] = d in membership[c]
        gaps = [
            d
            for d in order
            if d not in membership[c] and sources[d]["doc_date"] > sources[first]["doc_date"]
        ]
        rec["missing_from_later_lists"] = ";".join(gaps)
        recs.append(rec)
    cities = pd.DataFrame(recs)
    for r in cities.itertuples():
        if r.missing_from_later_lists:
            issues["Cities that leave a later list"].append(
                {
                    "document": r.missing_from_later_lists.replace(";", ", "),
                    "page": "",
                    "detail": f"{r.city} (first listed {r.first_listed_date} in {r.first_listed_doc}) is absent from these later lists",
                }
            )

    # ---------------------------------------------------------------- totals
    for (doc, tidx), g in F[F.measure != ""].groupby(["source_doc", "table_idx"]):
        printed = T[(T.source_doc == doc) & (T.table_idx == tidx)]
        cols = next(t for i, t in enumerate(sources[doc]["tables"]) if i == tidx)
        nums = []
        for v in printed.values_raw:
            nums += _nums(v)
        nums = sorted(set(nums))
        ua = g[g.level != "state"]  # state_merged values still add up to the column total
        for meas, gm in ua.groupby("measure"):
            s = round(gm.value.sum(), 3)
            if not nums:
                issues["Totals not printed / not found"].append(
                    {
                        "document": doc,
                        "page": ",".join(map(str, cols["pages"])),
                        "detail": f"{meas}: rows sum to {s}",
                    }
                )
                continue
            best = min(nums, key=lambda x: abs(x - s))
            diff = round(s - best, 3)
            if abs(diff) > ROUNDING:
                issues["Column sums that differ from the printed total"].append(
                    {
                        "document": doc,
                        "page": ",".join(map(str, cols["pages"])),
                        "detail": f"{meas}: rows sum to {s}; nearest printed total {best} (difference {diff:+})",
                    }
                )
            elif diff:
                issues["Rounding-level differences (<= 0.015 crore)"].append(
                    {
                        "document": doc,
                        "page": ",".join(map(str, cols["pages"])),
                        "detail": f"{meas}: rows sum to {s}; printed {best} (difference {diff:+})",
                    }
                )
        # Finance Commission annexes: UA rows within each state vs the state subtotal row
        if (g.level == "state").any():
            st = g[g.level == "state"].groupby(["state_raw", "measure"]).value.sum()
            uas = g[g.level == "ua"].groupby(["state_raw", "measure"]).value.sum()
            for (state, meas), v in st.items():
                u = uas.get((state, meas), 0.0)
                if abs(u - v) > ROUNDING:
                    issues["State subtotals that differ from their UA rows"].append(
                        {
                            "document": doc,
                            "page": ",".join(map(str, cols["pages"])),
                            "detail": f"{state}, {meas}: UA rows sum to {round(u, 3)}; state row prints {v}",
                        }
                    )

    # ---------------------------------------------------------------- row-level checks
    wide = F[(F.measure != "") & (~F.level.isin(["state", "state_merged"]))].pivot_table(
        index=["source_doc", "page", "sno", "city_raw"],
        columns="measure",
        values="value",
        aggfunc="first",
    )
    for idx, r in wide.iterrows():
        doc, page, sno, raw = idx
        fy = [
            c for c in r.index if c.startswith("released_fy") and "_to_" not in c and pd.notna(r[c])
        ]
        tot = [c for c in r.index if c.startswith("released_total") and pd.notna(r[c])]
        if len(fy) >= 2 and tot and abs(sum(r[c] for c in fy) - r[tot[0]]) > ROUNDING:
            issues["Rows whose yearly releases do not add to the row total"].append(
                {
                    "document": doc,
                    "page": page,
                    "detail": f"{sno} {raw}: {' + '.join(f'{r[c]}' for c in fy)} != {r[tot[0]]}",
                }
            )
        rel = [c for c in r.index if c.startswith(("released", "distributed")) and pd.notna(r[c])]
        use = [c for c in r.index if c.startswith("utilised") and pd.notna(r[c])]
        if rel and use:
            top = max(r[c] for c in rel)
            if r[use[0]] > top + ROUNDING:
                issues["Utilised more than released (as printed)"].append(
                    {
                        "document": doc,
                        "page": page,
                        "detail": f"{sno} {raw}: utilised {r[use[0]]} > released {top}",
                    }
                )

    # ---------------------------------------------------------------- cross-document: cumulative releases
    series = [
        ("ls17_au5104_2022_04_04", "released_to_2021_03_31"),
        ("ls17_au2467_2022_08_01", "released_total_to_2022_06"),
        ("ls17_au307_2024_02_05", "released_fy2020_21_to_2022_23"),
        ("ls17_au164_2023_12_04", "released_fy2020_21_to_2023_24"),
        ("ls18_au2080_2024_12_09", "released_to_fy2023_24"),
    ]
    single = F[F.cities.map(len) == 1].assign(city=lambda d: d.cities.map(lambda c: c[0]))
    cum = {}
    for doc, meas in series:
        s = (
            single[(single.source_doc == doc) & (single.measure == meas)]
            .groupby("city")
            .value.sum()
        )
        cum[doc] = s
    for c in sorted(set().union(*[set(s.index) for s in cum.values()])):
        vals = [(doc, cum[doc].get(c)) for doc, _ in series if c in cum[doc].index]
        for (d1, v1), (d2, v2) in zip(vals, vals[1:], strict=False):
            same_channel = not (
                d1.startswith("ls17_au2467")
                and d2 in ("ls17_au307_2024_02_05", "ls17_au164_2023_12_04")
            )
            if same_channel and v2 + ROUNDING < v1:
                issues["Cumulative releases that fall in a later document"].append(
                    {"document": f"{d1} -> {d2}", "page": "", "detail": f"{c}: {v1} then {v2}"}
                )

    # ---------------------------------------------------------------- allocations: AU164 vs Finance Commission
    alloc_fc = defaultdict(float)
    for doc, meas in [
        ("xvfc_2020_21_annex_5_3", "allocated_air_quality_2020_21"),
        ("xvfc_2021_26_vol2_annex_7_6", "allocated_air_quality_2021_22"),
        ("xvfc_2021_26_vol2_annex_7_6", "allocated_air_quality_2022_23"),
        ("xvfc_2021_26_vol2_annex_7_6", "allocated_air_quality_2023_24"),
    ]:
        for r in single[
            (single.source_doc == doc) & (single.measure == meas) & (single.level == "ua")
        ].itertuples():
            alloc_fc[r.city] += r.value or 0
    au = single[
        (single.source_doc == "ls17_au164_2023_12_04")
        & (single.measure == "allocated_fy2020_21_to_2023_24")
    ]
    for r in au.itertuples():
        fc = alloc_fc.get(r.city)
        if fc is not None and abs(fc - r.value) > 1.0:
            issues["Allocations: Lok Sabha answer vs Finance Commission reports"].append(
                {
                    "document": "ls17_au164_2023_12_04 vs xvfc annexes",
                    "page": r.page,
                    "detail": f"{r.city}: AU164 allocation FY20-21..23-24 = {r.value}; Annex 5.3 + 7.6 = {fc}",
                }
            )

    # ---------------------------------------------------------------- write
    F_out = F.assign(cities=F.cities.map(lambda c: ";".join(c)))
    F_out.to_csv(INTERIM / "ncap_funding_clean.csv", index=False)
    cities.to_csv(INTERIM / "ncap_cities.csv", index=False)
    summary = _summary(cities, F, sources, list_docs)
    _report(issues, summary, sources)
    return {k: len(v) for k, v in issues.items()}


def _summary(
    cities: pd.DataFrame, F: pd.DataFrame, sources: dict, list_docs: list[str]
) -> list[str]:
    lines = ["## Reconciled facts", ""]
    for d in list_docs:
        n = int(cities[f"in_{d}"].sum())
        lines.append(f"- {sources[d]['doc_date']} `{d}`: {n} cities.")
    lines.append("")
    by_first = cities.groupby("first_listed_date").city.apply(list)
    lines.append("First listing (date added) of the cities in the 2022 master list:")
    lines.append("")
    for date, cs in by_first.items():
        master_cs = [c for c in cs if c in set(cities[cities.in_master_131].city)]
        lines.append(
            f"- {date}: {len(master_cs)} cities"
            + (f" ({', '.join(master_cs)})" if len(master_cs) <= 25 else "")
        )
    lines.append("")
    x = cities[cities.in_master_131]
    lines.append(
        f"Funding channel among the 131 master cities: {int((x.channel == 'XVFC').sum())} XV-FC "
        f"(appear in an XV-FC table), {int((x.channel == 'NCAP').sum())} NCAP."
    )
    latest = list_docs[-1]
    y = cities[cities[f"in_{latest}"]]
    gone = cities[cities.in_master_131 & ~cities[f"in_{latest}"]]
    lines.append(
        f"In the latest list ({sources[latest]['doc_date']}, `{latest}`): {len(y)} cities, "
        f"{int((y.channel == 'XVFC').sum())} XV-FC and {int((y.channel == 'NCAP').sum())} NCAP. "
        f"Master cities absent from it: {', '.join(f'{r.city} ({r.channel})' for r in gone.itertuples()) or 'none'}."
    )
    lines.append("")
    return lines


def _report(issues: dict, summary: list[str], sources: dict) -> None:
    out = [
        "# NCAP extraction: mismatches to check by hand",
        "",
        "*Generated by `python -m src.acquire.ncap_validate`. Do not edit by hand; record "
        "conclusions in `docs/DECISIONS.md`.*",
        "",
        "Each item names the document (see `config/ncap_sources.yaml` for its URL) and the PDF "
        "page. Nothing below has been corrected in the data.",
        "",
    ]
    out += summary
    n = sum(len(v) for v in issues.values())
    out += [f"## Checks that need a human ({n} items)", ""]
    for title, items in issues.items():
        out += [
            f"### {title} ({len(items)})",
            "",
            "| ✓ | document | page | detail |",
            "|---|---|---|---|",
        ]
        for it in items:
            out.append(
                f"| ☐ | {it['document']} | {it['page']} | {str(it['detail']).replace('|', '/')} |"
            )
        out.append("")
    (DOCS / "ncap_extraction_mismatches.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    print(run())
