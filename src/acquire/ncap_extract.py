"""Extract NCAP city lists and funding tables from the PDFs in data/raw/ncap_docs/.

Driven by config/ncap_sources.yaml. Every output row records source_doc, page and
table_idx, and keeps the raw cell text next to the parsed number, so any value can be
checked against the document by hand. Nothing is corrected here: odd values are kept
as printed and flagged by ncap_validate.

Outputs (data/interim/):
  ncap_city_lists.csv       one row per city entry per list document
  ncap_funding.csv          long format: one row per (document, table row, measure)
  ncap_printed_totals.csv   the "Total" figures printed in each table

    python -m src.acquire.ncap_extract
"""

import csv
import re
from pathlib import Path

import pdfplumber

from src.acquire.ncap_pdfs import documents
from src.common.paths import INTERIM, raw_dir

# Spellings of states/UTs as they appear in the documents, mapped to one name.
STATES = {
    "andhra pradesh": "Andhra Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chandigarh": "Chandigarh",
    "chhattisgarh": "Chhattisgarh",
    "chattisgarh": "Chhattisgarh",
    "delhi": "Delhi",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jammu & kashmir": "Jammu & Kashmir",
    "jammu and kashmir": "Jammu & Kashmir",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "meghalaya": "Meghalaya",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "tamil nadu": "Tamil Nadu",
    "tamilnadu": "Tamil Nadu",
    "telangana": "Telangana",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
}
_STATE_RE = re.compile(
    r"^(" + "|".join(sorted((re.escape(s) for s in STATES), key=len, reverse=True)) + r")\b",
    re.I,
)
NUM_RE = re.compile(r"^-?\d[\d,]*(\.\d+)?$")
DASH = {"-", "–", "—", "nil", "NIL", "Nil"}


def clean(cell) -> str:
    text = re.sub(r"\s+", " ", str(cell)).strip() if cell is not None else ""
    # A number printed vertically in a merged cell comes out as "3 . 6 2": rejoin it.
    if re.fullmatch(r"\d(?:\s*[\d.]\s*)+", text) and " " in text:
        text = text.replace(" ", "")
    return text


def parse_number(raw: str) -> float | None:
    """Printed amount -> float. A dash means nothing (0); blank means not printed (None).
    A footnote asterisk ('*4.95') is ignored here; the raw text keeps it and emit() notes it."""
    raw = raw.strip().strip("*").strip()
    if raw in DASH:
        return 0.0
    if NUM_RE.match(raw):
        return float(raw.replace(",", ""))
    return None


def state_prefix(text: str) -> tuple[str | None, str]:
    """('Andhra Pradesh', rest) if text starts with a state name, else (None, text)."""
    m = _STATE_RE.match(text.strip())
    if not m:
        return None, text
    return STATES[m.group(1).lower()], text.strip()[m.end() :].strip()


def open_page(pdf: pdfplumber.PDF, number: int, rotate: int = 0) -> pdfplumber.page.Page:
    """1-based page, optionally rotated so that landscape tables read left to right."""
    page = pdf.pages[number - 1]
    if rotate:
        page.page_obj.rotate = (page.page_obj.rotate + rotate) % 360
        page = pdfplumber.page.Page(pdf, page.page_obj, page_number=number, initial_doctop=0)
    return page


# ------------------------------------------------------------------ city lists

# 2017 list: "Status" (PM10 / NO2) and "Major sources" columns share lines with the entries.
_STATUS = re.compile(r"\b(PM\s?10|PM\s?2\.5|NO\s?2)\b,?|\b[ivx]+\)\s.*$", re.I)
_ENTRY_TAIL = re.compile(r"\s+(PM\s?10|PM\s?2\.?5|NO2|PM10,.*|i+\).*|\(\d+\).*)$", re.I)


def parse_city_list(doc: dict, spec: dict, pdf: pdfplumber.PDF) -> list[dict]:
    """Numbered entries in reading order. The next expected item number anchors the parse, so
    state serial numbers and state counts like '(13)' on the same line are not taken as items."""
    rows, expected, state = [], 1, None
    for pno in spec["pages"]:
        text = open_page(pdf, pno).extract_text() or ""
        for line in text.splitlines():
            line = _STATUS.sub(" ", clean(line)).strip()
            if spec.get("strip_trailing_numbers"):  # value columns after the city name
                line = re.sub(r"(?:\s+-?\d[\d.,]*)+$", "", line)
            st, _ = state_prefix(re.sub(r"^\d+\s+", "", line))
            if st:
                state = st
            while True:
                m = re.search(
                    rf"(?:^|\s){expected}\.?\s+([A-Za-z][^\d]*?)(?=\s+\d{{1,3}}\.?\s+[A-Za-z]|$)",
                    line,
                )
                if not m:
                    break
                name = _ENTRY_TAIL.sub("", m.group(1)).strip()
                st_in, rest = state_prefix(name)
                if st_in and rest:  # "3. Andhra Pradesh Nellore" never happens, but guard anyway
                    name = rest
                marker = "*" if name.endswith("*") else ""
                rows.append(
                    {
                        "source_doc": doc["id"],
                        "doc_date": doc["doc_date"],
                        "page": pno,
                        "table_idx": spec["_idx"],
                        "item_no": expected,
                        "state_raw": state or "",
                        "city_raw": name.rstrip("*").strip(),
                        "marker": marker,
                    }
                )
                expected += 1
                line = line[m.end() :]
    return rows


# ------------------------------------------------------------------ funding tables (pdfplumber)


def _is_num(c: str) -> bool:
    return c in DASH or parse_number(c) is not None


def _split_row(cells: list[str]) -> tuple[str, list[str], list[str]]:
    """Compact a table row into (serial number, text cells, trailing numeric cells)."""
    vals = [c for c in cells if c]
    sno = vals.pop(0).rstrip(".") if vals and re.match(r"^\d{1,3}\.?$", vals[0]) else ""
    nums = []
    while vals and _is_num(vals[-1]):
        nums.insert(0, vals.pop())
    return sno, vals, nums


def parse_funding_table(
    doc: dict, spec: dict, pdf: pdfplumber.PDF
) -> tuple[list[dict], list[dict]]:
    """Row-by-row parse of a pdfplumber table, tolerant of the column grid changing between
    pages. States are taken only from the row itself (merged state cells are not carried
    forward, because pdfplumber attaches them to an arbitrary row). Rows missing from the
    detected tables are recovered from the page text by their serial number."""
    cols = {int(k): v for k, v in spec["columns"].items()}
    measures = [
        f for _, f in sorted(cols.items()) if f not in ("sno", "state", "city", "state_sno")
    ]
    width = spec.get("width", max(cols) + 1)
    has_sno = "sno" in cols.values()
    out, totals, prev = [], [], None
    seen: dict[int, dict] = {}

    def emit(base: dict, nums: list[str], note: str = "") -> None:
        if len(nums) == len(measures):
            pairs = list(zip(measures, nums, strict=True))
        elif 0 < len(nums) < len(measures):
            pairs = list(zip(measures, nums, strict=False))
            note = (
                note + "; " if note else ""
            ) + f"{len(measures) - len(nums)} trailing column(s) blank (merged cell?)"
        else:
            out.append(
                {
                    **base,
                    "measure": "",
                    "value_raw": " ".join(nums),
                    "value": None,
                    "parse_note": (note + "; " if note else "")
                    + f"{len(nums)} numbers for {len(measures)} columns",
                }
            )
            return
        for field, raw in pairs:
            n = (
                note
                if "*" not in raw
                else (note + "; " if note else "") + "asterisk in cell: see the document's footnote"
            )
            out.append(
                {
                    **base,
                    "measure": field,
                    "value_raw": raw,
                    "value": parse_number(raw),
                    "parse_note": n,
                }
            )

    for pno in spec["pages"]:
        page = open_page(pdf, pno)
        for t_idx, table in enumerate(page.extract_tables()):
            for r_idx, row in enumerate(table):
                cells = [clean(c) for c in row]
                if any(re.match(r"^total\b", c, re.I) for c in cells):
                    nums = [c for c in cells if _is_num(c) and c not in DASH]
                    totals.append(
                        {
                            "source_doc": doc["id"],
                            "table_idx": spec["_idx"],
                            "page": pno,
                            "pdf_table_idx": t_idx,
                            "row_idx": r_idx,
                            "label": "Total",
                            "values_raw": " ".join(nums),
                            "origin": "table",
                        }
                    )
                    continue
                if len(cells) == width:  # the configured grid: read cells by position
                    f = {name: cells[i] for i, name in cols.items()}
                    sno = (
                        f.get("sno", "").rstrip(".")
                        if re.match(r"^\d{1,3}\.?$", f.get("sno", ""))
                        else ""
                    )
                    texts = [t for t in (f.get("state", ""), f.get("city", "")) if t]
                    nums = [f[m] for m in measures]
                    while nums and not nums[-1]:
                        nums.pop()
                    if nums and not all(_is_num(c) for c in nums if c):
                        sno, texts, nums = _split_row(cells)
                    else:
                        nums = [c if c else "" for c in nums]
                else:
                    sno, texts, nums = _split_row(cells)
                base = {
                    "source_doc": doc["id"],
                    "doc_date": doc["doc_date"],
                    "table_idx": spec["_idx"],
                    "channel": spec.get("channel", ""),
                    "page": pno,
                    "pdf_table_idx": t_idx,
                    "row_idx": r_idx,
                }
                if (sno or not has_sno) and texts:
                    st, rest = state_prefix(texts[0])
                    state = st or ""
                    city = texts[-1] if len(texts) > 1 else (rest if st else texts[0])
                    if st and len(texts) == 1 and not rest:
                        city = ""  # only a state label on this row
                    if not city or re.search(
                        r"^(city|cities|million plus|state|name of)", city, re.I
                    ):
                        continue
                    prev = {**base, "sno": sno, "state_raw": state, "city_raw": city}
                    if sno:
                        seen[int(sno)] = prev
                    if nums:
                        emit(prev, nums)
                        prev["_has_vals"] = True
                    else:
                        out.append(
                            {
                                **prev,
                                "measure": "",
                                "value_raw": "",
                                "value": None,
                                "parse_note": "no values on this row (member of a UA, or values on the next row)",
                            }
                        )
                    continue
                if not sno and nums and prev is not None:
                    mine = [
                        r
                        for r in out
                        if r["page"] == prev["page"]
                        and r["row_idx"] == prev["row_idx"]
                        and r["source_doc"] == prev["source_doc"]
                    ]
                    blank = [r for r in mine if r["measure"] and r["value_raw"] == ""]
                    if not prev.get("_has_vals"):
                        out[:] = [r for r in out if not (r in mine and r["measure"] == "")]
                        emit(
                            {**prev, "page": pno, "row_idx": r_idx},
                            nums,
                            "values on the following row (wrapped cell)",
                        )
                        prev["_has_vals"] = True
                    elif blank and len([c for c in nums if c]) <= len(blank):
                        # e.g. a row wrapped over a page break whose merged utilisation cell stayed behind
                        for r, raw in zip(blank, [c for c in nums if c], strict=False):
                            r.update(
                                value_raw=raw,
                                value=parse_number(raw),
                                page=pno,
                                row_idx=r_idx,
                                parse_note=((r["parse_note"] + "; ") if r["parse_note"] else "")
                                + "values on the following row (wrapped across a page break)",
                            )

    if has_sno and seen:
        texts = {pno: (open_page(pdf, pno).extract_text() or "") for pno in spec["pages"]}
        for n in range(1, max(seen) + 1):
            if n in seen:
                continue
            for pno, text in texts.items():
                m = re.search(rf"(?m)^{n}\.?\s+(.+)$", text)
                if not m:
                    continue
                parsed = split_name_numbers(clean(m.group(1)), min_numbers=1)
                if not parsed:
                    continue
                name, nums = parsed
                st, rest = state_prefix(name)
                base = {
                    "source_doc": doc["id"],
                    "doc_date": doc["doc_date"],
                    "table_idx": spec["_idx"],
                    "channel": spec.get("channel", ""),
                    "page": pno,
                    "pdf_table_idx": "",
                    "row_idx": "",
                    "sno": str(n),
                    "state_raw": st or "",
                    "city_raw": rest if st else name,
                }
                emit(base, nums, "recovered from page text (row not in the detected table)")
                seen[n] = base
                break

    for pno in spec["pages"][-1:]:
        text = open_page(pdf, pno).extract_text() or ""
        m = re.search(r"(?ms)^Total\b(.{0,200})", text)
        if m:
            nums = re.findall(r"(?<![\w.])\d[\d,]*\.?\d*(?![\w.])", m.group(1))
            totals.append(
                {
                    "source_doc": doc["id"],
                    "table_idx": spec["_idx"],
                    "page": pno,
                    "pdf_table_idx": "",
                    "row_idx": "",
                    "label": "Total",
                    "values_raw": " ".join(nums),
                    "origin": "text",
                }
            )
    return out, totals


# ------------------------------------------------------------------ Finance Commission annexes (text lines)


def split_name_numbers(line: str, min_numbers: int = 3) -> tuple[str, list[str]] | None:
    """'Vijayawada U.A 1.48 514 -' -> ('Vijayawada U.A', ['1.48', '514', '-']).
    Token-based (no nested regex quantifiers, which backtrack badly on long number rows)."""
    tokens = line.split()
    i = len(tokens)
    while i > 0 and (tokens[i - 1] in DASH or NUM_RE.match(tokens[i - 1])):
        i -= 1
    name, nums = " ".join(tokens[:i]), tokens[i:]
    if len(nums) < min_numbers or not name or not re.match(r"^[A-Za-z]", name):
        return None
    return name, nums


def parse_annex_lines(doc: dict, spec: dict, pdf: pdfplumber.PDF) -> tuple[list[dict], list[dict]]:
    out, totals, state = [], [], None
    for pno in spec["pages"]:
        text = open_page(pdf, pno, spec.get("rotate", 0)).extract_text() or ""
        for line_no, line in enumerate(text.splitlines()):
            parsed = split_name_numbers(clean(line))
            if not parsed:
                continue
            name, nums = parsed
            st, rest = state_prefix(name)
            level = "state" if st and not rest else ("total" if name.lower() == "total" else "ua")
            if level == "state":
                state = st
            if "columns" in spec:
                fields = spec["columns"]
                # Short rows (e.g. Kerala: no air-quality grant) print only the leading columns.
                note = (
                    ""
                    if len(nums) == len(fields)
                    else f"{len(nums)} numbers for {len(fields)} columns (read from the left)"
                )
                pairs = list(zip(fields, nums, strict=False))
            else:  # first number = population, the rest assigned from the right
                right = spec["columns_from_right"]
                pairs = [(spec["first_number"], nums[0])]
                pairs += [(f, v) for f, v in zip(right, reversed(nums[1:]), strict=False)]
                missing = len(right) - (len(nums) - 1)
                note = f"{missing} column(s) not printed (read from the right)" if missing else ""
                pairs += [(f, "") for f in right[len(nums) - 1 :]]
            if level == "total":
                totals.append(
                    {
                        "source_doc": doc["id"],
                        "table_idx": spec["_idx"],
                        "page": pno,
                        "pdf_table_idx": "",
                        "row_idx": line_no,
                        "label": name,
                        "values_raw": " ".join(nums),
                        "origin": "text",
                    }
                )
                continue
            base = {
                "source_doc": doc["id"],
                "doc_date": doc["doc_date"],
                "table_idx": spec["_idx"],
                "channel": spec.get("channel", ""),
                "page": pno,
                "pdf_table_idx": "",
                "row_idx": line_no,
                "sno": "",
                "state_raw": state or "",
                "city_raw": name if level == "ua" else "",
                "level": level,
            }
            if not pairs:
                out.append(
                    {
                        **base,
                        "measure": "",
                        "value_raw": " ".join(nums),
                        "value": None,
                        "parse_note": note,
                    }
                )
            for field, raw in pairs:
                out.append(
                    {
                        **base,
                        "measure": field,
                        "value_raw": raw,
                        "value": parse_number(raw) if raw else None,
                        "parse_note": note,
                    }
                )
    return out, totals


# ------------------------------------------------------------------ driver

FUNDING_COLS = [
    "source_doc",
    "doc_date",
    "table_idx",
    "channel",
    "page",
    "pdf_table_idx",
    "row_idx",
    "sno",
    "state_raw",
    "city_raw",
    "level",
    "measure",
    "value_raw",
    "value",
    "parse_note",
]
LIST_COLS = [
    "source_doc",
    "doc_date",
    "page",
    "table_idx",
    "item_no",
    "state_raw",
    "city_raw",
    "marker",
]
TOTAL_COLS = [
    "source_doc",
    "table_idx",
    "page",
    "pdf_table_idx",
    "row_idx",
    "label",
    "values_raw",
    "origin",
]


def _write(path: Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def extract_all(raw: Path | None = None, out_dir: Path | None = None) -> dict[str, int]:
    raw, out_dir = raw or raw_dir("ncap_docs"), out_dir or INTERIM
    lists, funding, totals = [], [], []
    for doc in documents():
        with pdfplumber.open(raw / f"{doc['id']}.pdf") as pdf:
            for idx, spec in enumerate(doc["tables"]):
                spec = {**spec, "_idx": idx}
                if spec["kind"] == "city_list":
                    lists += parse_city_list(doc, spec, pdf)
                elif spec["kind"] == "funding_table":
                    rows, tot = parse_funding_table(doc, spec, pdf)
                    funding += [{**r, "level": r.get("level", "city")} for r in rows]
                    totals += tot
                elif spec["kind"] == "annex_lines":
                    rows, tot = parse_annex_lines(doc, spec, pdf)
                    funding += rows
                    totals += tot
    _write(out_dir / "ncap_city_lists.csv", lists, LIST_COLS)
    _write(out_dir / "ncap_funding.csv", funding, FUNDING_COLS)
    _write(out_dir / "ncap_printed_totals.csv", totals, TOTAL_COLS)
    return {"list_rows": len(lists), "funding_rows": len(funding), "totals": len(totals)}


if __name__ == "__main__":
    print(extract_all())
