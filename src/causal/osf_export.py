"""A clean copy of the analysis plan for upload to OSF: docs/osf/analysis_plan_osf.{md,html,pdf}.

The plan in docs/analysis_plan.md stays the source of truth. The copy differs only in presentation:
- the generated-number markers (<!--g:key-->value<!--/g-->) are removed, the values kept;
- the repository status paragraph is replaced by a version line naming the plan's commit;
- links to other repository files become links to that commit on GitHub.

The copy is made only from a committed, unmodified plan, so it always matches a commit hash.

    python -m src.causal.osf_export
"""

import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from markdown_it import MarkdownIt

from src.causal.pregate_report import MARK, PLAN
from src.common.paths import DOCS, ROOT

OUT = DOCS / "osf"
REPO_URL = "https://github.com/breenu/ncap-evaluation"
STATUS = re.compile(r"^\*Status:.*?\*[ \t]*$", re.MULTILINE)
REL_LINK = re.compile(r"\]\((?!https?://|#)([^)]+)\)")
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge",
    "google-chrome",
    "chromium",
]
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 17pt; margin: 0 0 6pt; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; border-bottom: 1px solid #bbb; padding-bottom: 2pt; }
p, li { margin: 3pt 0; }
table { border-collapse: collapse; margin: 6pt 0; font-size: 8.5pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 2pt 5pt; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
code { font-family: Consolas, monospace; font-size: 8.5pt; }
em { color: #333; }
hr { border: none; border-top: 1px solid #bbb; }
a { color: #1a4f8b; }
"""


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def version_line(commit: str, date: str) -> str:
    return (
        f"*Pre-registration, version of {date}. Source: `docs/analysis_plan.md` at commit `{commit}` of "
        f"{REPO_URL}. Every number in this plan was produced by the project's pipeline from data up to 2018 "
        "only. References of the form DEC-nnn point to `docs/DECISIONS.md`, and file paths to the repository, "
        "at that commit.*"
    )


def clean(text: str, commit: str, date: str) -> str:
    """The registered copy of the plan text (see module docstring)."""
    if len(STATUS.findall(text)) != 1:
        raise ValueError("expected exactly one status paragraph starting '*Status:'")
    text = MARK.sub(lambda m: m.group(2), text)
    text = STATUS.sub(lambda _: version_line(commit, date), text)
    text = REL_LINK.sub(lambda m: f"]({REPO_URL}/blob/{commit}/docs/{m.group(1)})", text)
    if "<!--" in text:
        raise ValueError("an HTML comment survived the export")
    return re.sub(r"\n{3,}", "\n\n", text)


def to_html(md_text: str) -> str:
    body = MarkdownIt("commonmark").enable("table").render(md_text)
    title = re.search(r"^# (.+)$", md_text, re.MULTILINE).group(1)
    return (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{CSS}</style></head><body>\n{body}</body></html>\n")  # fmt: skip


def print_pdf(html: Path, pdf: Path) -> bool:
    browser = next((b for b in BROWSERS if Path(b).exists() or shutil.which(b)), None)
    if browser is None:
        print("no Edge/Chrome found: wrote Markdown and HTML only")
        return False
    pdf.unlink(missing_ok=True)  # never mistake an old PDF for a new one
    subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.resolve().as_uri()],
                   check=True, capture_output=True, timeout=120)  # fmt: skip
    # Edge's launcher can exit before the PDF is written: wait until it exists and stops growing.
    size = -1
    for _ in range(120):
        if pdf.exists() and pdf.stat().st_size > 0 and pdf.stat().st_size == size:
            return True
        size = pdf.stat().st_size if pdf.exists() else -1
        time.sleep(0.5)
    return False


def main() -> None:
    rel = PLAN.relative_to(ROOT).as_posix()
    if git("status", "--porcelain", "--", rel):
        sys.exit(f"{rel} has uncommitted changes: commit it first, so the copy matches a commit hash")
    commit = git("log", "-1", "--format=%H", "--", rel)
    date = git("log", "-1", "--format=%cs", "--", rel)
    md_text = clean(PLAN.read_text(encoding="utf-8"), commit, date)

    OUT.mkdir(exist_ok=True)
    md_path, html_path, pdf_path = (OUT / f"analysis_plan_osf.{ext}" for ext in ("md", "html", "pdf"))
    md_path.write_text(md_text, encoding="utf-8")
    html_path.write_text(to_html(md_text), encoding="utf-8")
    made = [md_path, html_path] + ([pdf_path] if print_pdf(html_path, pdf_path) else [])
    print(f"plan commit {commit} ({date})")
    for f in made:
        print(f"  {f.relative_to(ROOT).as_posix()}  sha256 {hashlib.sha256(f.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
