#!/usr/bin/env python3
"""
export_cost_study.py — Build the E4 cost-study instrument for the catalogers.

E4 (journal plan, RQ4): measure what LLM metadata enrichment COSTS in
cataloger time and editing effort, compared with cataloging from scratch.

Per cataloger (default 2-3):
  - 80 records TOTAL, counterbalanced: 40 in Condition M (manual) and 40 in
    Condition V (verify LLM draft). M and V sets are DISJOINT within a
    cataloger; overlap across catalogers is allowed (it is needed for
    cross-cataloger agreement, and the pool is 204 gold-bearing records).
  - Condition order counterbalanced across catalogers (cataloger 1 starts
    with M, cataloger 2 starts with V, cataloger 3 starts with M, ...).
  - Manual input for BOTH conditions is title/author/year ONLY — the same
    input the LLM cataloger saw, so M vs V is a fair comparison of effort.

Outputs (phase1/data/panel/e4/):
  cataloger_<X>_items.jsonl   per-cataloger sample incl. gold + LLM draft
                               (RESEARCHER ONLY — gold must not reach catalogers)
  cataloger_<X>_instrument.html  click-through instrument with per-record
                               timer, condition banner, fields for final
                               headings/DDC; V condition shows the LLM draft.
                               Downloads cataloger_<X>_results.csv.
  cataloger_<X>_workbook.csv  same records as a fillable spreadsheet fallback
                               (id, condition, title, author, year, [LLM
                               draft for V], time_s, final_subjects, final_ddc)
  cataloger_<X>_instructions.md  one-page sheet for that cataloger

Usage:
  python3 phase1/scripts/export_cost_study.py            # 2 catalogers
  python3 phase1/scripts/export_cost_study.py --catalogers 3
"""

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECS = ROOT / "data" / "libra_cat_records_scaled.jsonl"
PREDS = ROOT / "data" / "libra_cat_predictions.jsonl"
OUT = ROOT / "data" / "panel" / "e4"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Cataloging study — {title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         max-width: 780px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  h1 {{ font-size: 1.25rem; }}
  .cond {{ display:inline-block; padding: 2px 10px; border-radius: 4px;
           font-weight: 600; font-size: .85rem; }}
  .M {{ background: #e3f2fd; color: #0d47a1; }}
  .V {{ background: #fde8e8; color: #b02a2a; }}
  #progress {{ color: #888; font-size: .9rem; margin: .5rem 0; }}
  .bar {{ height: 6px; background:#e2e2e2; border-radius:3px; }}
  .bar > div {{ height:6px; background:#2d7ff9; border-radius:3px; width:0%; }}
  .card {{ border:1px solid #ccc; border-radius:10px; padding:1.1rem 1.3rem; margin:1rem 0; }}
  .rec {{ font-size:1.05rem; }}
  .rec .t {{ font-weight:600; }}
  .rec .m {{ color:#555; }}
  .draft {{ background:#fdf6ec; border-left:4px solid #e8a33d; padding:.6rem .8rem;
           margin:.8rem 0; font-size:.92rem; }}
  label {{ display:block; font-weight:600; margin-top:.8rem; }}
  textarea {{ width:100%; min-height:70px; font-family:inherit; font-size:.95rem; }}
  input[type=text] {{ width:100%; font-family:inherit; font-size:.95rem; }}
  .timer {{ font-size:1.5rem; font-weight:700; font-variant-numeric:tabular-nums;
           margin:.6rem 0; }}
  .nav {{ display:flex; gap:.6rem; margin:1rem 0; }}
  .nav button {{ flex:1; padding:.7rem; cursor:pointer; border-radius:8px;
                 border:2px solid #ccc; background:#fff; font-size:1rem; }}
  .nav button.primary {{ background:#2d7ff9; color:#fff; border-color:#2d7ff9; }}
  #msg {{ color:#b02a2a; }}
  details {{ font-size:.88rem; color:#555; margin-bottom:1rem; }}
  details summary {{ cursor:pointer; color:#2d7ff9; }}
  #dl {{ background:#2d7ff9; color:white; border:none; padding:.6rem 1.1rem;
        border-radius:8px; cursor:pointer; font-size:1rem; }}
</style>
</head>
<body>
<h1>Cataloging study — {title}</h1>
<p id="progress"></p>
<div class="bar"><div id="barfill"></div></div>

<details>
  <summary>Instructions (read once)</summary>
  <p>You are cataloging public-domain books from their catalog record only
  (title, author, year). For each item:</p>
  <ul>
    <li><b>Condition M (manual):</b> assign LCSH subject headings and a DDC
        number from scratch, as you would in retrospective conversion.</li>
    <li><b>Condition V (verify):</b> a machine-generated draft is shown; edit
        it into your final headings and DDC. Drafts are AI-generated — you
        decide what to keep, change, or remove.</li>
  </ul>
  <p>Enter one subject heading per line. DDC: enter a Dewey number (3+ digits).
  Use the timer: it starts when an item appears — work until you are done,
  then press <b>Next</b>. Take breaks between items if needed; the timer only
  runs while an item is on screen.</p>
</details>

<div id="stage"></div>
<div class="nav">
  <button id="prev">&#8592; Prev</button>
  <span id="msg"></span>
  <button id="next" class="primary">Next &#8594; (stops timer)</button>
</div>
<button id="dl">&#11015; Download results CSV</button>

<script>
"use strict";
const ITEMS = {items};
const KEY = {key};
let state = {{
  idx: 0,
  rows: {{}},          // id -> {{time_s, subjects, ddc}}
  visibleSince: null,  // ms epoch when current item appeared
}};
const timers = {{}};

function nowMs() {{ return Date.now(); }}
function load() {{
  try {{ const s = localStorage.getItem(KEY); if (s) state = JSON.parse(s); }} catch (e) {{}}
}}
function save() {{
  try {{ localStorage.setItem(KEY, JSON.stringify(state)); }} catch (e) {{}}
}}
function esc(s) {{
  return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}}
function fmt(sec) {{
  sec = Math.round(sec || 0);
  const m = Math.floor(sec / 60), s = sec % 60;
  return m + ":" + String(s).padStart(2, "0");
}}
function tick() {{
  const el = document.getElementById("timer");
  if (el && state.visibleSince) el.textContent = fmt((nowMs() - state.visibleSince) / 1000);
}}

function render() {{
  const i = state.idx, it = ITEMS[i];
  const done = Object.keys(state.rows).length;
  document.getElementById("progress").textContent =
    "Item " + (i+1) + " of " + ITEMS.length + " · " + done + "/" + ITEMS.length + " completed";
  document.getElementById("barfill").style.width = (100*done/ITEMS.length) + "%";
  const row = state.rows[it.id] || {{ subjects: "", ddc: "" }};
  const condClass = it.condition === "M" ? "M" : "V";
  let html = '<div class="card"><div class="rec">' +
    '<span class="cond ' + condClass + '">Condition ' + it.condition + '</span>' +
    '<div class="t">' + esc(it.title) + '</div>' +
    '<div class="m">' + esc(it.author) + (it.year ? " · " + esc(it.year) : "") + '</div></div>';
  if (it.condition === "V") {{
    html += '<div class="draft"><strong>Machine draft — edit as needed:</strong><br>' +
      '<em>Subjects:</em> ' + esc((it.llm_subjects || []).join(" ; ")) + '<br>' +
      '<em>DDC:</em> ' + esc(it.llm_ddc || "(none)") + '</div>';
  }}
  html += '<div class="timer" id="timer">0:00</div>' +
    '<label>Final subject headings (one per line)</label>' +
    '<textarea id="subjects" placeholder="e.g. Whaling -- Fiction">' + esc(row.subjects) + '</textarea>' +
    '<label>Final DDC number</label>' +
    '<input type="text" id="ddc" value="' + esc(row.ddc) + '" placeholder="e.g. 813.52">';
  document.getElementById("stage").innerHTML = html + "</div>";
  // restart timer only when the item has never been seen
  if (state.visibleSince == null || state.rows[it.id] == null) state.visibleSince = nowMs();
  document.getElementById("msg").textContent = "";
  save();
}}

function capture() {{
  const it = ITEMS[state.idx];
  const subjects = document.getElementById("subjects").value.trim();
  const ddc = document.getElementById("ddc").value.trim();
  const prev = state.rows[it.id] || {{}};
  let time_s = prev.time_s || 0;
  if (state.visibleSince) {{
    time_s += (nowMs() - state.visibleSince) / 1000;
    state.visibleSince = null;
  }}
  state.rows[it.id] = {{ time_s: Math.round(time_s), subjects: subjects, ddc: ddc }};
  save();
}}

function goNext() {{
  capture();
  if (state.idx < ITEMS.length - 1) {{ state.idx += 1; state.visibleSince = null; render(); }}
  else {{
    const missing = ITEMS.filter(it => !state.rows[it.id] || !state.rows[it.id].subjects);
    document.getElementById("msg").textContent = missing.length
      ? missing.length + " item(s) still have no headings — use Prev to check, or download anyway."
      : "All items completed. Download your results.";
    state.visibleSince = null; save();
  }}
}}
document.getElementById("next").addEventListener("click", goNext);
document.getElementById("prev").addEventListener("click", () => {{
  capture();
  if (state.idx > 0) {{ state.idx -= 1; state.visibleSince = null; render(); }}
}});
setInterval(tick, 500);

function csvField(v) {{
  v = String(v == null ? "" : v);
  return /[",\\n]/.test(v) ? '"' + v.replace(/"/g,'""') + '"' : v;
}}
function download() {{
  const header = ["id","condition","title","author","year","llm_subjects","llm_ddc","time_s","final_subjects","final_ddc"];
  const rows = ITEMS.map(it => {{
    const r = state.rows[it.id] || {{ time_s: 0, subjects: "", ddc: "" }};
    return [it.id, it.condition, it.title, it.author, it.year,
            (it.llm_subjects || []).join(" ; "), it.llm_ddc || "",
            r.time_s, r.subjects, r.ddc];
  }});
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

INSTRUCTIONS_MD = """# Cataloging study — instructions (cataloger {x})

Thank you for taking part. You will catalog **{n} public-domain books**
({n_m} manually, {n_v} by verifying a machine draft), about
**{hours} hours** of work total. You may do it in one sitting or split across
sessions — open the instrument file and continue where you left off.

## What you see per book
- **Title, author, year** — this is ALL the catalog information available,
  the same as in retrospective conversion of sparse records.
- **Condition M (manual):** assign LCSH subject headings (one per line) and a
  DDC number from scratch.
- **Condition V (verify):** a machine-generated draft (subjects + DDC) is
  shown. Edit it into your final version — keep, change, add, or delete as you
  see fit. Drafts are AI-generated; you are not told which model.

## Rules
1. One subject heading per line, LCSH form where possible (you may use
   established heading strings, with subdivisions after ` -- `).
2. DDC: enter a number with at least three digits (e.g., `813.52`).
3. Work at your normal professional pace. The per-item timer runs only while
   an item is on screen — pause between items freely.
4. There is no "right answer": different catalogers legitimately differ. We
   are measuring effort and agreement, not grading you.

## After finishing
Click **Download results CSV** and send us `{outfile}`.
Keep the original HTML file in case you need to resume.

Questions: {contact}
"""


def load():
    recs = [json.loads(l) for l in open(RECS, encoding="utf-8") if l.strip()]
    preds = {json.loads(l)["work_key"]: json.loads(l)
             for l in open(PREDS, encoding="utf-8") if l.strip()}
    # the records file contains a few duplicated work_keys; keep one row each
    seen = set()
    unique = []
    for r in recs:
        if r["work_key"] in seen:
            continue
        seen.add(r["work_key"])
        unique.append(r)
    usable = [r for r in unique
              if r.get("gold_subjects") and r.get("ddc")
              and r["work_key"] in preds and not preds[r["work_key"]].get("error")]
    return usable, preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogers", type=int, default=2,
                    help="number of catalogers (pool allows up to 3 with overlap)")
    ap.add_argument("--per-cataloger", type=int, default=80,
                    help="records per cataloger (default 80 = 40 M + 40 V)")
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    usable, preds = load()
    n_cond = args.per_cataloger // 2
    if args.per_cataloger > 2 * len(usable):
        raise SystemExit(f"need {args.per_cataloger} distinct records/cataloger "
                         f"but only {len(usable)} gold-bearing records")
    print(f"usable gold-bearing records: {len(usable)}")

    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    for x in range(1, args.catalogers + 1):
        pool = usable[:]
        rng.shuffle(pool)
        # disjoint M and V within this cataloger
        m_recs = pool[:n_cond]
        v_recs = pool[n_cond:2 * n_cond]
        # condition order counterbalanced across catalogers
        start_m = (x % 2 == 1)  # cataloger 1 starts M, cataloger 2 starts V, ...
        cond_seq = (["M"] * n_cond + ["V"] * n_cond) if start_m \
            else (["V"] * n_cond + ["M"] * n_cond)
        rec_by_cond = {"M": m_recs, "V": v_recs}
        items = []
        for i, cond in enumerate(cond_seq):
            r = rec_by_cond[cond].pop(0) if rec_by_cond[cond] else None
            if r is None:
                continue
            p = preds[r["work_key"]]
            author = "; ".join(r.get("author_name") or [])
            items.append({
                "id": f"E4-{x}-{i+1:03d}",
                "condition": cond,
                "work_key": r["work_key"],
                "title": r.get("title", ""),
                "author": author,
                "year": r.get("first_publish_year") or "",
                "gold_subjects": r.get("gold_subjects") or [],
                "gold_ddc": (r.get("ddc") or [""])[0],
                "llm_subjects": p.get("pred_subjects") or [],
                "llm_ddc": p.get("pred_ddc") or "",
            })
        # order within each condition is already random via pool shuffle;
        # write items but strip gold from the cataloger-facing files
        master = OUT / f"cataloger_{x}_items.jsonl"
        master.write_text("\n".join(json.dumps(it) for it in items) + "\n")

        public = []
        for it in items:
            pub = {k: it[k] for k in ("id", "condition", "title", "author",
                                      "year", "llm_subjects", "llm_ddc")}
            # manual rows must never carry the draft in cataloger-facing files
            if pub["condition"] == "M":
                pub["llm_subjects"] = []
                pub["llm_ddc"] = ""
            public.append(pub)

        # HTML instrument (public fields only)
        items_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
        html = HTML_TEMPLATE.format(
            title=f"Cataloging study — cataloger {x}",
            items=items_json,
            key=json.dumps(f"cost_study_{x}"),
            outfile=json.dumps(f"cataloger_{x}_results.csv"))
        (OUT / f"cataloger_{x}_instrument.html").write_text(html, encoding="utf-8")

        # CSV workbook fallback
        with open(OUT / f"cataloger_{x}_workbook.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "condition", "title", "author", "year",
                        "llm_subjects", "llm_ddc", "time_s", "final_subjects",
                        "final_ddc"])
            for it in public:
                w.writerow([it["id"], it["condition"], it["title"], it["author"],
                            it["year"], " ; ".join(it["llm_subjects"]),
                            it["llm_ddc"], "", "", ""])

        # one-page instructions
        n_m = sum(1 for it in items if it["condition"] == "M")
        n_v = sum(1 for it in items if it["condition"] == "V")
        hours = round(args.per_cataloger * 2.2 / 60, 1)  # ~2.2 min/item est.
        (OUT / f"cataloger_{x}_instructions.md").write_text(
            INSTRUCTIONS_MD.format(x=x, n=args.per_cataloger, n_m=n_m, n_v=n_v,
                                   hours=hours,
                                   outfile=f"cataloger_{x}_results.csv",
                                   contact="[your email]"))
        print(f"cataloger {x}: {len(items)} items "
              f"({n_m} M / {n_v} V), starts with {'M' if start_m else 'V'}")

    print(f"\nwrote instrument files to {OUT}")
    print("master items (with gold) stay here — do NOT send to catalogers")


if __name__ == "__main__":
    main()
