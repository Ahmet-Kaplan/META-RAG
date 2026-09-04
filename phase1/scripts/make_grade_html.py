#!/usr/bin/env python3
"""
make_grade_html.py — Generate a click-through grading page for one labeler.

Reads a labeler CSV (id,question,title,authors,subjects,grade) from the
relevance pilot and writes a self-contained HTML file that:

  - shows ONE item at a time: the patron's request + the candidate book
    (title / authors / subjects) — exactly the catalog info a librarian
    would have;
  - grades with buttons 0 / 1 / 2 (keyboard: keys 0,1,2; Left/Right to move);
  - auto-saves progress to localStorage (reopen and continue);
  - downloads a graded CSV (same rows, grade column filled) for
    score_relevance_pilot.py.

The CSV is parsed HERE (Python csv handles quoted commas/quotes), and the
rows are embedded as JSON — the browser never parses CSV, so nothing can
mis-split on the commas inside author/subject strings.

Usage:
  python3 phase1/scripts/make_grade_html.py                # both labelers
  python3 phase1/scripts/make_grade_html.py --only A       # one labeler
"""

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pilot" / "relevance"
RUBRIC_PATH = OUT / "rubric.md"

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Relevance grading — {title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         max-width: 760px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  h1 {{ font-size: 1.3rem; }}
  #progress {{ font-size: .9rem; color: #888; margin-bottom: .25rem; }}
  .bar {{ height: 6px; background: #e2e2e2; border-radius: 3px; margin-bottom: 1rem; }}
  .bar > div {{ height: 6px; background: #2d7ff9; border-radius: 3px; width: 0%; }}
  .card {{ border: 1px solid #ccc; border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 1rem; }}
  .q {{ font-size: 1.05rem; }}
  .book {{ margin-top: 1rem; }}
  .book .t {{ font-weight: 600; font-size: 1.1rem; }}
  .book .meta {{ color: #555; margin-top: .2rem; }}
  .book .subj {{ color: #555; margin-top: .4rem; font-size: .92rem; }}
  .tag {{ display:inline-block; background:#eee; border-radius: 4px; padding: 0 6px;
         font-size:.8rem; color:#444; margin-left:.4rem; }}
  .btns {{ display: flex; gap: .6rem; margin: 1rem 0; }}
  .btns button {{ flex: 1; font-size: 1.2rem; padding: .8rem; cursor: pointer;
        border-radius: 8px; border: 2px solid #ccc; background: #fff; }}
  .btns button.sel {{ border-color: #2d7ff9; background: #e8f1ff; }}
  .btns button:hover {{ border-color: #2d7ff9; }}
  .nav {{ display: flex; justify-content: space-between; gap: .6rem; margin-bottom: 2rem; }}
  .nav button, #dl {{ padding: .55rem 1rem; border-radius: 8px; cursor: pointer; }}
  #msg {{ color: #b02a2a; }}
  details {{ font-size: .88rem; color: #555; margin-bottom: 1.5rem; }}
  details summary {{ cursor: pointer; color: #2d7ff9; }}
  #dl {{ background: #2d7ff9; color: white; border: none; font-size: 1rem; }}
  .done {{ font-size: 1.1rem; font-weight: 600; margin: 1rem 0; }}
</style>
</head>
<body>
<h1>Relevance grading — {title}</h1>
<p id="progress"></p>
<div class="bar"><div id="barfill"></div></div>

<details>
  <summary>Judging instructions (rubric)</summary>
  <pre style="white-space:pre-wrap; font-family:inherit">{rubric}</pre>
</details>

<div id="stage"></div>

<div class="btns">
  <button data-g="0">0 — not relevant</button>
  <button data-g="1">1 — marginally relevant</button>
  <button data-g="2">2 — clearly relevant</button>
</div>

<div class="nav">
  <button id="prev">&#8592; Previous</button>
  <span id="msg"></span>
  <button id="next">Next &#8594;</button>
</div>

<button id="dl">&#11015; Download graded CSV</button>

<script>
"use strict";
const ITEMS = {items};
const KEY = {key};
let state = {{ idx: 0, grades: {{}} }};

function load() {{
  try {{ const s = localStorage.getItem(KEY); if (s) state = JSON.parse(s); }} catch (e) {{}}
}}
function save() {{
  try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{}}
}}
const stage = document.getElementById("stage");
const msg = document.getElementById("msg");
function answered() {{ return Object.values(state.grades).filter(g => g === 0 || g === 1 || g === 2).length; }}
function render() {{
  const i = state.idx;
  const it = ITEMS[i];
  const n = answered();
  const total = ITEMS.length;
  document.getElementById("progress").textContent =
    "Item " + (i + 1) + " of " + total + " · " + n + "/" + total + " graded";
  document.getElementById("barfill").style.width = (100 * n / total) + "%";
  const cur = state.grades[it.id];
  stage.innerHTML =
    '<div class="card">' +
      '<div class="q"><strong>Patron request:</strong> ' + esc(it.question) + '</div>' +
      '<div class="book">' +
        '<div class="t">' + esc(it.title) + (it.authors ? '<span class="tag">' + esc(it.authors) + '</span>' : '') + '</div>' +
        (it.subjects ? '<div class="subj"><em>Subjects:</em> ' + esc(it.subjects) + '</div>' : '') +
      '</div>' +
    '</div>';
  document.querySelectorAll(".btns button").forEach(b => {{
    b.classList.toggle("sel", String(cur) === b.dataset.g);
  }});
  msg.textContent = "";
  save();
}}
function esc(s) {{
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}}
function grade(g) {{
  const it = ITEMS[state.idx];
  state.grades[it.id] = g;
  if (state.idx < ITEMS.length - 1) {{ state.idx += 1; }}
  render();
}}
document.querySelectorAll(".btns button").forEach(b =>
  b.addEventListener("click", () => grade(parseInt(b.dataset.g, 10))));
document.getElementById("prev").addEventListener("click", () => {{
  if (state.idx > 0) {{ state.idx -= 1; render(); }}
}});
document.getElementById("next").addEventListener("click", () => {{
  if (state.idx < ITEMS.length - 1) {{ state.idx += 1; render(); }}
}});
document.addEventListener("keydown", (e) => {{
  if (e.key === "0" || e.key === "1" || e.key === "2") {{ grade(parseInt(e.key, 10)); }}
  else if (e.key === "ArrowLeft") {{ if (state.idx > 0) {{ state.idx -= 1; render(); }} }}
  else if (e.key === "ArrowRight") {{ if (state.idx < ITEMS.length - 1) {{ state.idx += 1; render(); }} }}
}});

function csvField(v) {{
  v = String(v == null ? "" : v);
  return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}}
function download() {{
  const missing = ITEMS.filter(it => !(it.id in state.grades) ||
                 !(state.grades[it.id] === 0 || state.grades[it.id] === 1 || state.grades[it.id] === 2));
  if (missing.length) {{
    msg.textContent = missing.length + " item(s) still ungraded — download anyway? Click again to confirm.";
    if (!window.__confirmDl) {{ window.__confirmDl = true; return; }}
  }}
  const header = ["id", "question", "title", "authors", "subjects", "grade"];
  const rows = ITEMS.map(it => [it.id, it.question, it.title, it.authors, it.subjects,
                                (it.id in state.grades ? state.grades[it.id] : "")]);
  const csv = [header, ...rows].map(r => r.map(csvField).join(",")).join("\\n");
  const blob = new Blob([csv], {{ type: "text/csv;charset=utf-8" }});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = {outfile};
  a.click();
}}
document.getElementById("dl").addEventListener("click", download);

load();
render();
</script>
</body>
</html>
"""


def read_rows(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["A", "B"], default=None)
    args = ap.parse_args()

    rubric = RUBRIC_PATH.read_text(encoding="utf-8") if RUBRIC_PATH.exists() else ""
    # HTML-escape the rubric text (it is plain text shown inside <pre>)
    import html as html_mod
    rubric = html_mod.escape(rubric)

    labelers = ["A", "B"] if not args.only else [args.only]
    for lab in labelers:
        src = OUT / f"labeler_{lab}.csv"
        rows = read_rows(src)
        items = [{k: (r.get(k) or "") for k in ("id", "question", "title",
                                                "authors", "subjects")}
                 for r in rows]
        key = f"relevance_pilot_{lab}"
        out_name = f"labeler_{lab}.graded.csv"
        # embed as JSON, but escape "</script" so item text cannot break out
        items_json = json.dumps(items, ensure_ascii=False)
        items_json = items_json.replace("</", "<\\/")
        html = TEMPLATE.format(title=f"Labeler {lab}", items=items_json,
                               key=json.dumps(key), rubric=rubric,
                               outfile=json.dumps(out_name))
        dest = OUT / f"grade_labeler_{lab}.html"
        dest.write_text(html, encoding="utf-8")
        print(f"wrote {dest} ({len(items)} items)")


if __name__ == "__main__":
    main()
