"""Wording check for every figure, caption, alt text and dashboard page (DEC-193).

H1 is not identified by this design (DEC-151), so no text may present anything as an effect of NCAP
(DEC-154 and the Phase 8 rule), and no text may rank cities (plan §5; DEC-167). `problems(text)` returns
the banned phrases found; `check(text, where)` raises if there are any. Figures are checked in
`style.save` before they are written, so a figure with banned wording is never saved.
"""

import re

# Phrases that are never allowed, whatever surrounds them.
BANNED = [
    (r"policy[\s-]+effects?", "'policy effect'"),
    (r"policy[\s-]+attributable", "'policy-attributable'"),
    (r"attributable\s+to\s+(?:ncap|the\s+programme|the\s+program|policy)", "'attributable to NCAP'"),
    (r"\bimpacts?\s+of\s+ncap", "'impact of NCAP'"),
    (r"\bncap\s+(?:caused|causes|reduced|reduces|cut|cuts|lowered|lowers|improved|improves|worked|works)\b",
     "'NCAP caused/reduced/...'"),
    (r"\b(?:due\s+to|because\s+of|thanks\s+to)\s+ncap", "'due to / because of NCAP'"),
    (r"\bcounterfactual", "'counterfactual' (say 'synthetic comparison' or 'comparison units')"),
    # "best quality" is MAIAC's own name for a QA level (DEC-175), not a ranking
    (r"\b(?:best|worst)\b(?![\s-]+quality)", "ranking language ('best'/'worst')"),
    (r"\btop[\s-]+\d+", "ranking language ('top N')"),
    (r"league\s+table", "ranking language ('league table')"),
]  # fmt: skip

# "effect(s) of NCAP" is allowed only when negated within the same clause, e.g. "not an effect of NCAP",
# "not effects of NCAP", "not identified as an effect of NCAP", "nothing here is an effect of NCAP".
EFFECT = re.compile(r"effects?\s+of\s+(?:ncap|the\s+programme)", re.IGNORECASE)
NEGATION = re.compile(r"\b(?:not|no|nothing|none|never|cannot|n't)\b", re.IGNORECASE)
CLAUSE_END = re.compile(r"[.;:!?\n(]")


def _negated(text: str, start: int) -> bool:
    """True if a negation word appears between the start of the clause and `start`."""
    head = text[:start]
    cut = max((m.end() for m in CLAUSE_END.finditer(head)), default=0)
    return bool(NEGATION.search(head[cut:]))


def problems(text: str) -> list[str]:
    t = " ".join(str(text).split())  # line breaks inside labels are not clause ends for this purpose
    found = [label for pat, label in BANNED if re.search(pat, t, re.IGNORECASE)]
    for m in EFFECT.finditer(t):
        if not _negated(t, m.start()):
            found.append(f"un-negated 'effect of NCAP' near: '{t[max(0, m.start() - 40):m.end()]}'")
    return found


def check(text: str, where: str = "") -> None:
    p = problems(text)
    if p:
        raise ValueError(f"banned wording{' in ' + where if where else ''}: {'; '.join(p)}")


def figure_texts(fig) -> list[str]:
    """Every string drawn on a matplotlib figure (titles, labels, ticks, legends, annotations), one per
    text object, so a negation in one label cannot excuse wording in another."""
    from matplotlib.text import Text

    return [t.get_text() for t in fig.findobj(Text) if t.get_text()]


def check_figure(fig, where: str) -> None:
    for t in figure_texts(fig):
        check(t, where)
