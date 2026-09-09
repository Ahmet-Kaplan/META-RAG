# Extended journal paper — plan (retargeted to Knowledge-Based Systems)

**Status:** planning. Conference version (AIDL 2026, `paper/main.pdf`, 8pp) is frozen
and considered sufficient for that venue.
**Target (decided 2026-09-05):** *Knowledge-Based Systems* (KBS), Elsevier —
**SCIE** (Computer Science – Artificial Intelligence), Q1, IF ≈ 7–8.8 (2023 JCR;
verify current on the Clarivate Master Journal List).

Rationale for KBS over the earlier candidates:
- KBS explicitly publishes LLM+knowledge research — e.g., LLMs as oracles for
  instantiating ontologies, surveys of integrating LLMs with knowledge-based
  methods, LLM-driven conflict resolution in expert systems. Cataloging is, in
  KBS terms, **knowledge acquisition**: turning sparse records into structured
  subject knowledge (LCSH) and classification (DDC).
- The paper's spine — *does the acquired knowledge improve a downstream
  knowledge-based system (a metadata-aware retrieval index), and which
  knowledge fields carry the effect?* — is a KBS question, not a
  library-science question. The library is the application domain; the
  contribution is the measurement of LLM-acquired-knowledge utility.
- Strictly SCIE, good IF, and a better methodological fit for a
  benchmark/evaluation study than the DSS decision-support framing. NCA is no
  longer in WoS and is dropped; DSS is dropped as the framing target (kept in
  `plan/dss_submission_framing.md` as an alternative lens).

**Constraint:** journal extension needs ≥30% new material over the proceedings
paper; KBS research articles are typically 8,000–12,000 words, so the expansion
is expected, not optional.

---

## 1. Framing for KBS: LLM cataloging as knowledge acquisition

The obvious move — bigger corpus, more models, human validation — produces a
more rigorous version of the same paper. That is a weak journal submission: the
contribution is still "we measured that LLM gap-filling helps discovery," and a
KBS reviewer who has seen the conference paper learns nothing new.

The conference paper answers *whether* LLM-generated subject knowledge helps a
metadata-aware retriever. It does not answer the questions a
knowledge-engineering reader asks: **what kind of knowledge does an LLM
reliably acquire from a sparse record, which knowledge fields does a downstream
system actually use, and can the acquired knowledge be trusted against
professional judgment?**

**KBS framing (knowledge-engineering emphasis):** treat the LLM as an
automated **knowledge-acquisition component** whose output (LCSH subject
knowledge + DDC classification) is carried through the full KE cycle —
acquisition from sparse input, validation against professional gold (with an
inter-cataloger agreement ceiling and live authority checking), and utility
measurement in the consuming knowledge-based system (the metadata-aware
retrieval index). The two knowledge representations under study (open,
pre-coordinated thesaurus strings vs. closed hierarchical classification) let
the paper ask the KE question *which representation of acquired knowledge a
downstream system actually uses*; the sparsity sweep asks *how value depends
on knowledge-base completeness*; the cost study (E4) prices machine- vs.
expert-acquired knowledge. The library is the case study; the object of study
is the acquisition channel itself.

Working titles (KE-led) in `plan/kbs_submission_framing.md`; recommended:
*"Knowledge Acquisition by LLMs: The Value of Machine-Acquired Subject
Knowledge for Knowledge-Based Retrieval."*

---

## 2. Research questions (through the KBS lens)

| RQ | Question | Knowledge-systems role | New? |
|---|---|---|---|
| RQ1 | How much retrieval gain does LLM-acquired subject knowledge produce, as a function of existing knowledge coverage? | **Utility of acquired knowledge vs. coverage** — the headline result | Extends conference RQ5 to a 10× corpus |
| RQ2 | How good is LLM knowledge acquisition against *validated professional* gold, and against an inter-cataloger agreement ceiling? | **Acquisition accuracy**, calibrated against expert agreement | **New** — panel Activity 1 |
| RQ3 | What drives acquisition quality: model, conditioning (sparse record vs. full text), or knowledge type (thesaurus headings vs. hierarchical classification)? | **Which acquisition lever**, mechanistically explained | **New** — multi-model + conditioning ablation |
| RQ4 | What does acquisition cost in expert time — from scratch vs. verifying LLM output? | **Cost of machine- vs. expert-acquired knowledge** | **New** — panel Activity 2 |
| RQ5 | Where is the break-even? Knowledge-utility gain per expert-hour, by coverage level. | **Deployment analysis** of the acquisition component | **New** — synthesis |

RQ5 is the synthesis; RQ1–RQ4 are its inputs.

---

## 3. What we already have vs. what must be collected

### Already in the repo (no new collection)
- `phase1/data/join_matches_scaled.jsonl` — **1,359 joined books**, all with
  Gutenberg LCSH, 536 with OL DDC. Corpus can go 227 → ~1,300 by downloading
  full text and re-indexing. The single biggest credibility win; costs compute.
- `phase1/data/libra_cat_predictions*.jsonl` — 687+ LLM cataloging predictions.
- `phase2/reports/confidence_per_question.json` — per-question scores, full pool.
- `phase2/reports/pooled_eval.*` — full-pool pooled graded relevance (n=338)
  and the human-calibration pilot (`phase1/data/pilot/relevance/`, two raters,
  κ human–LLM 0.64–0.80 vs human–human 0.755).
- `phase1/protocols/` — both panel activities written; E4 instrument built
  (`export_cost_study.py`, `score_cost_study.py`).
- Working pipeline: index → retrieve → evaluate → bootstrap CI → pooled judging.

### Must be collected
| Item | Blocker | Effort |
|---|---|---|
| **Cataloger panel (2–3 professionals)** | Recruitment — the critical path | ~3.5 h each; ours: scheduling + analysis |
| Full text for ~1,100 more books | Gutenberg rate limits | Compute, ~1 day |
| LOC authority/search API data | Blocked from sandbox | Hours, on user's machine |
| Independently sourced topical queries | See §5 | Design work |
| 2 more LLM cataloging models (E3) | API budget | Hours + cost |

---

## 4. Experiment plan

### E1 — Scale the corpus (RQ1)
227 → ~1,300 books. Re-run: per-type table, sparsity sweep, loop conditions,
all with bootstrap CIs on the full question pool. Expect the sparsity curve to
hold with tighter intervals — the **knowledge-utility-vs-coverage function**.

### E2 — Validated gold + agreement ceiling (RQ2)
Panel Activity 1 on a stratified sample (~60 of 600 records). Produces (a)
corrected gold, (b) an **inter-cataloger agreement baseline**. With it, the
34.2% exact / 63.3% any-level figures become interpretable: if two
professionals agree exactly on only ~40% of headings, an LLM at 34% is
near-human, not poor. This calibrates the knowledge-acquisition claim.

### E3 — What drives acquisition quality (RQ3)
Three factors, factorial where affordable:
- **Model**: deepseek-chat + 2 others (one frontier, one small/open).
- **Conditioning**: title+author only vs. + full text (we have full text for
  the corpus; the conference paper flags this as unrun).
- **Knowledge type**: LCSH (open, pre-coordinated thesaurus) vs. DDC (closed,
  hierarchical classification) — already shown to differ sharply (34% vs 83%).
*Expect: full text helps thesaurus-style subject analysis more than
classification — a mechanistic explanation of the LCSH/DDC gap.*

### E4 — The cost side (RQ4)
Panel Activity 2 (instrument ready in `phase1/data/panel/e4/`): each cataloger
drafts N=40 records from scratch and verifies LLM drafts for another N=40.
Measures: time/record, edits/record, final quality. Counterbalanced; report
per-cataloger. Analysis: `score_cost_study.py`.

### E5 — Synthesis (RQ5)
Combine E1's gain-vs-coverage with E4's expert-time-per-record: knowledge
utility gain per expert-hour as a function of coverage, with the break-even
identified.

---

## 5. The threat we still have not fixed

Topical questions are LLM paraphrases of each record's own subject heading.
Pooled graded judging + the human calibration fixed the *scoring*; the *query
distribution* is still unrepresentative, so topical numbers remain an upper
bound. Options, best first:
1. **Real query logs** from a partner library (anonymised subject searches).
2. **Authority-sourced queries** — sample LCSH headings from `id.loc.gov`
   independently of the corpus, then pool-judge relevance. **Recommended.**
3. Human relevance judgments — done for the pooled sample; extend to (2).

Do at least (2). A KBS reviewer evaluating a knowledge-utility claim will
discount the gain function if the queries were derived from the very knowledge
being tested.

---

## 6. Scope discipline — what NOT to do

- **Multilingual.** The Gutenberg index is 3,987/4,000 English. Separate paper.
- **A better retriever.** META-RAG is BM25F + dense twin; conceded. Add a
  reranker only as a baseline if demanded.
- **A third benchmark.** LIBRA-Eval is enough; validate, do not extend.
- **Framing as an LIS/cataloging paper.** KBS reviewers are AI/knowledge
  engineers. Knowledge acquisition + utility measurement first; the library is
  the application domain.

---

## 7. Sequencing

The panel is the critical path and the only item requiring other people.

| Phase | Work | Depends on |
|---|---|---|
| 0 | Panel recruitment + scheduling | — (start immediately) |
| 1 | E1 corpus scale-up; E3 model/conditioning ablations | compute only |
| 2 | E2 + E4 panel sessions | Phase 0 |
| 3 | §5 option 2 (authority-sourced queries) | Phase 1 |
| 4 | E5 synthesis, figures, draft | Phases 1–3 |

**Fallback if the panel fails.** Without catalogers there is no agreement
ceiling (E2) and no cost measurement (E4). RQ5 collapses; the paper reverts to
a scaled-up conference paper. In that case retarget to *Applied Intelligence*
(SCIE, more tolerant of single-model system studies) or *Expert Systems with
Applications*, framed around E1+E3+§5 rather than the full economics.

---

## 8. Open questions for the author

1. Can you recruit 2–3 professional catalogers, and on what timeline?
2. Is a partner library plausible for query logs (§5 option 1)?
3. Budget for the multi-model comparison (E3)?
4. Confirm KBS's current JIF and SCIE status on the Clarivate Master Journal
   List; check the guide-for-authors for length and format expectations.
