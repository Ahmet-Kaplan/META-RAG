# Extended journal paper — plan (retargeted to Decision Support Systems)

**Status:** planning. Conference version (AIDL 2026, `paper/main.pdf`, 8pp) is frozen
and considered sufficient for that venue.
**Target (decided 2026-09-05):** *Decision Support Systems* (Elsevier) — **SCIE**
indexed, IF ≈ 6.8 (Q1). Rationale for this venue over IP&M/ESWA/NCA:
- The extended paper's spine is a *decision-support artifact* (cost-effectiveness
  of LLM metadata enrichment as a collection-management intervention) — that is
  DSS's home turf, not a side quest as it would be at IP&M.
- DSS explicitly publishes LLM/AI-assisted decision research (e.g., LLM-based
  process comprehension, narrative XAI with LLMs), so a generative-AI decision
  study is on-scope.
- Strictly SCIE (satisfies the requirement); NCA is no longer in WoS and is
  dropped as a fallback. Verify DSS on the Clarivate Master Journal List before
  committing.
**Constraint:** journal extension needs ≥30% new material over the proceedings
paper; DSS research articles are typically 8,000–12,000 words, so the expansion
is expected, not optional.

---

## 1. Framing for DSS: from "does it help" to "should we do it"

The obvious move — bigger corpus, more models, human validation — produces a
more rigorous version of the same paper. That is a weak journal submission: the
contribution is still "we measured that LLM gap-filling helps discovery," and a
reviewer who has seen the conference paper learns nothing new.

The conference paper answers *whether* LLM cataloging helps discovery. It does
not answer the decision a library actually has to settle before deploying
anything: **is it worth doing, given what it costs, for a catalog like ours?**
Nothing in the RAG or LLM-cataloging literature measures the cost side or gives
a manager a way to read the gain off their own coverage level.

**DSS framing:** combine the discovery-gain curve we already have (as a function
of subject-access coverage) with measured human effort, into a
**decision-support analysis of LLM metadata enrichment**: given a catalog's
current coverage, how much discovery gain per dollar/cataloger-hour does
enrichment buy, and where is the break-even? That is a decision the paper
supports with evidence — the DSS contribution.

Working title (DSS orientation):
*"Should We Let an LLM Finish the Catalog? A Decision-Support Analysis of
LLM Metadata Enrichment for Library Discovery"* — alternatives in
`plan/dss_submission_framing.md`.

---

## 2. Research questions (through the DSS lens)

| RQ | Question | Decision-support role | New? |
|---|---|---|---|
| RQ1 | How much discovery gain does metadata enrichment produce, as a function of existing subject-access coverage? | The **gain function** a manager reads their own coverage off | Extends conference RQ5 to a 10× corpus |
| RQ2 | How good is LLM cataloging against *validated professional* gold, and against an inter-cataloger agreement ceiling? | **Quality calibration** — without it, the gain numbers are not trustworthy | **New** — panel Activity 1 |
| RQ3 | What drives cataloging quality: model, full-text conditioning, or vocabulary type? | **Which intervention lever** to pull (which field, which model tier) | **New** — multi-model + full-text ablation |
| RQ4 | What does enrichment cost in cataloger time — drafting from scratch vs. verifying an LLM draft? | The **cost function** | **New** — panel Activity 2 |
| RQ5 | Where is the break-even? Cost per record against discovery gain per record, by coverage level. | The **decision rule** — the paper's spine | **New** — synthesis |

RQ5 is the contribution; RQ1–RQ4 are its inputs. In DSS terms: RQ1/RQ3 build
the decision model's benefit side, RQ4 the cost side, RQ2 the validity of both,
and RQ5 renders a decision curve.

---

## 3. What we already have vs. what must be collected

### Already in the repo (no new collection)
- `phase1/data/join_matches_scaled.jsonl` — **1,359 joined books**, all with
  Gutenberg LCSH, 536 with OL DDC. Corpus can go 227 → ~1,300 by downloading
  full text and re-indexing. This is the single biggest credibility win available
  and costs only compute.
- `phase1/data/libra_cat_predictions*.jsonl` — 687+ LLM cataloging predictions.
- `phase2/reports/confidence_per_question.json` — per-question scores, full pool.
- `phase2/reports/pooled_eval.*` — full-pool pooled graded relevance (n=338)
  and the human-calibration pilot (`phase1/data/pilot/relevance/`, two raters,
  κ human–LLM 0.64–0.80 vs human–human 0.755).
- `phase1/protocols/` — both panel activities, written and unrun.
- Working pipeline: index → retrieve → evaluate → bootstrap CI → pooled judging.

### Must be collected
| Item | Blocker | Effort |
|---|---|---|
| **Cataloger panel (2–3 professionals)** | Recruitment — the critical path | Their ~3.5h each; ours: scheduling, analysis |
| Full text for ~1,100 more books | Gutenberg rate limits | Compute, ~1 day |
| LOC authority/search API data | Blocked from sandbox; works from user's network | Hours, on user's machine |
| Independently sourced topical queries | See §5 | Design work |

---

## 4. Experiment plan

### E1 — Scale the corpus (RQ1)
227 → ~1,300 books. Re-run: Table I, sparsity sweep, loop conditions, all with
bootstrap CIs on the full question pool. Expect the sparsity curve to hold with
tighter intervals and a more credible coverage range — this is the **gain
function** the decision model reads.
*Risk: low. Mostly compute.*

### E2 — Validated gold + agreement ceiling (RQ2)
Panel Activity 1 on a stratified sample (~60 of 600 records). Produces (a)
corrected gold, (b) an **inter-cataloger agreement baseline** — the number the
conference paper repeatedly says LLM scores "must be read against" but does not
have. With it, the 34.2% exact / 63.3% any-level figures become interpretable:
if two professionals agree exactly on only ~40% of headings, an LLM at 34% is
near-human, not poor. This calibration is what makes the decision model's inputs
defensible.
*This is the highest-value single addition.*

### E3 — What drives cataloging quality (RQ3)
Three factors, factorial where affordable:
- **Model**: deepseek-chat + 2 others (one frontier, one small/open) — a
  single-model result is a standing reviewer objection.
- **Conditioning**: title+author only (current) vs. + full text. We have full
  text for every corpus book; the conference paper flags this as unrun.
- **Vocabulary**: LCSH vs. DDC (already shown to differ sharply — 34% vs 83%).
*Expect: full text helps subject analysis much more than classification. If so,
that explains the LCSH/DDC gap mechanistically rather than descriptively — and
tells a manager which field is worth the effort.*

### E4 — The cost side (RQ4)
Panel Activity 2, counterbalanced: each cataloger drafts N≈40 records from
scratch and verifies LLM drafts for another N≈40. Measure time/record,
edits/record, and final quality. Counterbalance order and record difficulty.
*Risk: highest. Small n, human variance, recruitment. Pre-register the analysis;
report per-cataloger, not just pooled.*

### E5 — Cost-effectiveness synthesis / decision model (RQ5)
Combine E1's gain-per-coverage-level with E4's minutes-per-record:
discovery gain per cataloger-hour, as a function of current coverage. Output a
**decision curve** a collection manager can read against their own catalog —
the DSS artifact the paper is built around.

---

## 5. The threat we still have not fixed

Topical questions are LLM paraphrases of each record's own subject heading.
Pooled graded judging (conference §V-G) fixed the *scoring*, and the
human-calibration pilot now validates the judge; the *query distribution* is
still unrepresentative. Every topical number remains an upper bound. Options,
best first:

1. **Real query logs.** Ask a partner library for anonymised subject-search
   logs. Strongest fix; depends on a partner and on privacy review.
2. **Authority-sourced queries.** Sample LCSH headings from `id.loc.gov`
   *independently of the corpus*, then pool-judge which corpus records are
   relevant. Removes the record→query dependency entirely. No partner needed.
   **Recommended default.**
3. **Human relevance judgments** — done for the pooled sample
   (`phase1/data/pilot/relevance/`); extend to the authority-sourced queries in
   (2).

Do at least (2) (plus (3) on those queries). Without it the journal version
inherits the conference version's ceiling, and a DSS reviewer evaluating the
decision model will discount the gain function.

---

## 6. Scope discipline — what NOT to do

- **Multilingual.** The Gutenberg index is 3,987/4,000 English. Multilingual
  cataloging needs a different corpus (DNB/BnF) and is a separate paper. Leave
  as future work.
- **A better retriever.** META-RAG is BM25F with a dense twin and we concede
  that. Do not add a cross-encoder and pretend the contribution is retrieval.
  Add a reranker only as a baseline if a reviewer demands it.
- **A third benchmark.** LIBRA-Eval is enough. Validate it; do not extend it.
- **Framing as an LIS paper.** DSS reviewers are IS/decision-science readers,
  not catalogers. Keep the decision model front and center; cataloging is the
  application domain, not the contribution.

---

## 7. Sequencing

The panel is the critical path and the only item requiring other people. Start
recruitment first; everything else is compute and can proceed in parallel.

| Phase | Work | Depends on |
|---|---|---|
| 0 | Panel recruitment + scheduling | — (start immediately) |
| 1 | E1 corpus scale-up; E3 model/conditioning ablations | compute only |
| 2 | E2 + E4 panel sessions | Phase 0 |
| 3 | §5 option 2 (authority-sourced queries) + option 3 (human relevance sample on them) | Phase 1 |
| 4 | E5 synthesis (decision model), figures, draft | Phases 1–3 |

**Fallback if the panel fails.** Without catalogers there is no agreement
ceiling (E2) and no cost measurement (E4) — RQ5 collapses and the paper reverts
to a scaled-up conference paper, which is not worth a Q1 submission. In that
case: retarget to *Expert Systems with Applications* or *Knowledge-Based
Systems* (both SCIE) on the strength of E1+E3+§5, framed around what drives LLM
cataloging quality (the RQ3 ablation) rather than around deployment economics.
Decide this before Phase 2, not after.

---

## 8. Open questions for the author

1. Can you recruit 2–3 professional catalogers, and on what timeline? Everything
   distinctive about this plan depends on it.
2. Is a partner library plausible for query logs (§5 option 1)? If yes it changes
   the strongest available fix.
3. Budget for multi-model comparison (E3) — which models are available?
4. Confirm DSS's current JIF and SCIE status on the Clarivate Master Journal
   List; check the guide-for-authors for length and reference-format
   expectations before drafting.
