# Human Validation of LLM Judgments — Runbook (AIDL 2026 reviewer comment 5)

**Date:** 2026-09-04
**Purpose:** address the reviewer's pending items — "human validation of LLM
relevance judgments" (this document) and the cataloger-panel baseline
(`cataloger_panel_materials.md`, separate, external recruitment).

There are **two LLM-judged outputs** in the paper that a reviewer can ask to
have human-validated, and this runbook covers both:

| Pilot | What the LLM judged | Data source | Who judges | Effort |
|---|---|---|---|---|
| **A. Relevance** (§V-G pooled graded) | ~11,242 (query, record) pairs graded 0/1/2 | `phase2/reports/pooled_qrels.json` | 2 careful readers (you + a colleague/RA; no cataloging degree needed) | ~40–60 min each for 120 pairs |
| **B. Faithfulness** (RQ2) | 120 answers rated faithful/unfaithful vs. cited sources | regenerate with `evaluate.py --answers-out` (answers were never persisted) | 2 careful readers | ~30–45 min each for 40 items |

Both pilots use **two independent labelers** on the **same items**, so we can
report: human–human agreement (is the task itself well-defined?) and
human–LLM agreement (does the LLM judge match a human?), as Cohen's κ.

---

## Study A — relevance judgments (pooled graded, §V-G)

### Why this exists
The pooled graded check that produced the honest gap-fill estimate (+0.106
single-gold → +0.057 graded over all 338 topical questions) was judged by
`deepseek-chat`. The reviewer wants to know the LLM judge agrees with humans.

### Step A1 — generate the workbooks (DONE, committed)
```bash
python3 phase1/scripts/export_relevance_pilot.py --per-labeler 120 --seed 7
```
Produces in `phase1/data/pilot/relevance/`:
- `items.jsonl` — master list **with LLM grades (not for labelers)**
- `labeler_A.csv`, `labeler_B.csv` — same 120 items, different order, blank
  grade column (grade 0/1/2, rubric below)
- `rubric.md` — judging instructions

Sample: 120 pairs across 18 topical queries, grade-enriched (LLM grades
2/1/0 ≈ 42/21/57) so the informative judgments are not drowned in
grade-0s.

### Step A2 — two labelers grade (guided UI, no spreadsheet editing)

Each labeler gets a **click-through grading page**, not a raw CSV:

```bash
python3 phase1/scripts/make_grade_html.py      # regenerates both pages
```

Produces `phase1/data/pilot/relevance/grade_labeler_A.html` and
`grade_labeler_B.html`. Each page:

- shows ONE item at a time: the patron's request + the candidate book
  (title / authors / subjects) — the catalog view a librarian would have;
- grades with buttons or keyboard (keys `0`, `1`, `2`; `←`/`→` to move);
- auto-saves progress to the browser's localStorage — close it and reopen
  to continue;
- has a **Download graded CSV** button that writes
  `labeler_A.graded.csv` / `labeler_B.graded.csv` in the page's format.

Labelers open the HTML in a browser (double-click), work through the items
(~20–30 s/pair → 120 pairs ≈ 40–60 min), and download the graded CSV when
done. The rubric is collapsible at the top of the page. Send each labeler
their own file (A or B); do NOT share `items.jsonl` (it contains the LLM
grades).

Regenerate with `--only A` or `--only B` if only one page is needed. The
pages embed the CSV rows as JSON (parsed by Python, not the browser), so the
commas inside author/subject strings cannot mis-split fields — verified by a
round-trip test through the scorer's own csv reader.

### Step A3 — score
```bash
# point the scorer at the downloaded graded CSV(s) by copying them into place:
cp labeler_A.graded.csv phase1/data/pilot/relevance/labeler_A.csv
cp labeler_B.graded.csv phase1/data/pilot/relevance/labeler_B.csv
python3 phase1/scripts/score_relevance_pilot.py
```
Report (`report.md` + stdout): coverage, human–human Cohen's κ (3-way and
relevant-vs-not), per-labeler human–LLM κ and exact agreement, confusion
matrix. Target for the paper: κ ≥ 0.6–0.7 human–LLM.

### Step A4 — (optional, stronger) graded-nDCG on human grades
The kappa answers "do humans agree with the LLM judge?" — enough for the
rebuttal. A stronger claim ("the +0.057 margin survives human grading")
needs full-query judging: pick 4–6 of the 18 sampled queries and have a
labeler grade **every** pooled candidate for those queries (add rows to the
CSV). Then recompute the graded-nDCG gap-fill on the human-graded subset. If
you want this, say so and I'll add the per-query recomputation to the scorer.

---

## Study B — faithfulness judgments (RQ2)

### Why a regeneration is needed
The RQ2 answers were generated once but **only 5 examples were persisted**
(`gen_pass_scaled.json`); the full 120 (question, answer, citations, judge
verdict) were discarded. To human-judge them we must regenerate with
persistence.

### Step B1 — regenerate the 120-question answer set with persistence
```bash
cd phase2
rm -f ../phase1/data/pilot/faithfulness/answers.jsonl
HF_HOME="$PWD/../.hf_cache" python3 scripts/evaluate.py \
    --index data/index_scaled_ts \
    --qa ../phase1/data/libra_qa_drafts_scaled_polished.jsonl \
    --corpus data/corpus_scaled.jsonl \
    --mode meta --questions 120 --generate \
    --report reports/gen_pass_scaled.md \
    --answers-out ../phase1/data/pilot/faithfulness/answers.jsonl
```
Cost: ~120 generation + ~120 judge calls ≈ **<$1**. (This re-runs the same
pass that produced the shipped RQ2 numbers; `--mode meta` keeps it to the
grounded condition that owns the reported faithfulness rate.)

`evaluate.py` now has an `--answers-out` flag (added for this pilot) that
persists each full answer with its cited sources rendered exactly as the
judge saw them, plus the judge verdict.

### Step B2 — generate the workbooks
```bash
python3 phase1/scripts/export_faithfulness_pilot.py --per-labeler 40 --seed 7
```
Takes **all** judge-unfaithful answers (the informative minority) plus a
random draw of judge-faithful ones up to the cap. Produces
`labeler_A.csv`/`labeler_B.csv`/`rubric.md` (answer + numbered sources; blank
"faithful" column: yes/no).

### Step B3 — two labelers fill the CSVs
Per rubric.md: faithful = every claim supported by the cited sources; a true
but unsupported claim is unfaithful; refusals count faithful. ~30–60 s/item
→ 40 items ≈ 30–45 min each.

### Step B4 — score
```bash
python3 phase1/scripts/score_faithfulness_pilot.py
```
Reports human–human and human–LLM κ, confusion, disagreement ids.

---

## What goes in the response letter / paper

One paragraph in the rebuttal (and the camera-ready Limitations → moved to
Methods), e.g.:

> To validate the LLM relevance judge, two human raters independently graded
> a stratified sample of N=120 pooled (query, record) pairs from §V-G;
> human–human agreement was κ=… and agreement with the LLM judge was κ=…
> (labeler A) / κ=… (labeler B). For the faithfulness judgments (RQ2), two
> raters judged M=40 regenerated answers against their cited sources;
> human–human κ=…, human–LLM κ=…. The LLM-judged numbers in §V-G/RQ2 are
> therefore calibrated against human judgments rather than assumed.

## Timeline & people

| Step | Who | Duration |
|---|---|---|
| A2 relevance labeling | 2 readers | 40–60 min each |
| B1 regeneration | you (API, <$1) | ~10–15 min |
| B2–B3 faithfulness labeling | 2 readers | 30–45 min each |
| A3/B4 scoring | you | 5 min |

The cataloger-panel baseline (the other half of the reviewer's comment)
remains a separate external study — materials in
`phase1/protocols/cataloger_panel_materials.md`, recruitment email in
`phase1/outreach_catalogers.md`; it converts the residual-589 bound into a
measured error-vs-alternative split and is not something a non-cataloger can
substitute.
