# KBS Submission Framing — Knowledge-Based Systems (Elsevier)

**Date:** 2026-09-05
**Source material:** AIDL 2026 conference paper (*Filling the Gaps: When LLM
Cataloging Improves Library Discovery*, `paper/main.tex`, 8 pp.) + the
retargeted extension plan (`plan/extended_journal_paper.md`).
**Venue:** *Knowledge-Based Systems* — SCIE (Computer Science – Artificial
Intelligence), Q1, IF ≈ 7–8.8 (2023 JCR). Verify current JIF and format on the
Clarivate Master Journal List and the [KBS guide for authors](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors).

---

## 1. How to see this paper the way KBS sees it

KBS publishes research on **knowledge-based systems**: knowledge acquisition,
representation, reasoning, and the systems that use knowledge to perform
tasks. KBS reviewers are AI/knowledge-engineering readers, and they will ask
three questions your conference version does not answer:

1. **What is the knowledge system?** — The LLM is a *knowledge-acquisition
   component* that turns sparse bibliographic records into structured subject
   knowledge (LCSH) and classification (DDC); the consuming system is a
   metadata-aware retrieval index.
2. **What does the paper contribute to knowledge engineering?** — A measured
   account of what LLM-acquired knowledge is *worth*: its acquisition
   accuracy (vs. professional gold), its utility to a downstream system
   (retrieval gain, decomposed by knowledge field and coverage), and its cost.
3. **Why is the evidence credible?** — Validated professional gold,
   inter-cataloger agreement ceiling, human-calibrated relevance judgments,
   released code/benchmark/data.

The library/discovery machinery is the **application domain**; the
**contribution is the knowledge-acquisition analysis**.

---

## 2. Working title options

1. *Knowledge Acquisition by LLMs for Library Discovery: What Machine-Acquired
   Subject Metadata Is Worth to a Retrieval Index* (mechanism-led; KBS voice)
2. *When Is Machine-Acquired Subject Knowledge Useful? An Analysis of
   LLM-Generated Metadata for Knowledge-Based Retrieval* (question-led)
3. *Acquiring Catalog Knowledge with LLMs: Accuracy, Downstream Utility, and
   Cost of Machine-Generated Subject Metadata* (three-part; matches the
   RQ2/RQ1/RQ4 structure)

Recommendation: **#1 or #3**. Avoid the passive "When LLM Cataloging
Improves…"; name the acquisition mechanism and its utility.

---

## 3. Abstract (target 200–250 words) — draft

> Knowledge-based retrieval depends on structured metadata that describes what
> a document is about, and for library collections that metadata is expensive
> and unevenly distributed: many records carry no subject knowledge at all.
> Large language models (LLMs) can draft such metadata cheaply, but the
> knowledge-engineering question is whether machine-acquired subject knowledge
> is accurate enough and useful enough to justify acquiring it. We answer that
> question with an end-to-end analysis of LLM-based knowledge acquisition for
> library discovery. Using a corpus of 1,300 public-domain books and a
> released two-sided benchmark, we (i) show that LLM-acquired subject headings
> measurably improve a metadata-aware retrieval index, and that the utility of
> the acquired knowledge is largest where existing knowledge coverage is
> thinnest — the gap-filling regime — and never reaches zero; (ii) decompose
> the effect by knowledge type, finding that thesaurus-style subject headings
> carry the entire retrieval gain while hierarchical classification
> contributes none, and explain the mechanism (open pre-coordinated headings
> vs. closed hierarchical classes); (iii) calibrate acquisition accuracy
> against validated professional gold and an inter-cataloger agreement
> ceiling, showing the LLM operates near the human agreement bound; and (iv)
> measure the cost of acquisition — expert time drafting metadata from scratch
> versus verifying LLM output. We synthesize these into a decision analysis:
> expected retrieval-gain per expert-hour as a function of a collection's
> coverage. Code, benchmark, and data are released for reuse.

---

## 4. Contribution list (KBS-framed)

1. **Knowledge-acquisition analysis (the paper's spine):** a measured account
   of LLM-acquired bibliographic knowledge — its accuracy, its downstream
   utility decomposed by knowledge type and coverage, and its cost — rather
   than a single quality number.
2. **Utility-by-field decomposition (RQ1 + field ablation):** which knowledge
   field a retrieval system actually consumes (subject headings carry +0.382
   topical nDCG@10 with CI [+0.333, +0.431]; DDC contributes ≈0), giving a
   knowledge-engineering reason to spend acquisition effort where it matters.
3. **Calibrated acquisition accuracy (RQ2–RQ3):** LLM knowledge acquisition
   scored against validated professional gold *and* an inter-cataloger
   agreement ceiling; plus a drivers analysis (model, conditioning, knowledge
   type) that explains the thesaurus/classification gap mechanistically.
4. **Cost of machine- vs. expert-acquired knowledge (RQ4):** expert minutes
   per record, drafting vs. verifying LLM output, from a counterbalanced
   panel study.
5. **Open artifacts:** code, benchmark, data, protocols, human relevance
   judgments, and judge calibration released.

---

## 5. Positioning paragraph (draft for Introduction)

> Knowledge-based systems are only as good as the knowledge they acquire, and
> acquiring structured knowledge about documents — what each one is about —
> remains a bottleneck in knowledge-based retrieval. Large language models now
> offer a cheap acquisition channel: they can propose subject knowledge from
> almost no input. But the knowledge-engineering literature evaluates such
> acquisition either in isolation (agreement against a single reference
> source) or not at all, and never measures whether the acquired knowledge
> improves the system that consumes it, which fields of the knowledge are
> load-bearing, or what acquisition costs relative to expert effort. This
> paper supplies that missing analysis for a concrete knowledge domain —
> bibliographic subject metadata — where professional knowledge is sparse,
> expensive, and unevenly distributed.

---

## 6. Structure map: conference paper → KBS manuscript

| KBS manuscript section | Content | Source |
|---|---|---|
| 1. Introduction | Knowledge-acquisition framing; gap; contributions | Conference §I rewritten |
| 2. Related work | Knowledge acquisition + LLM, metadata-aware retrieval, cataloging gold; position | Conference §II rewritten + comparison table |
| 3. System & knowledge model | META-RAG as knowledge-based retriever; LIBRA-Eval as the measurement apparatus; the acquisition component | Conference §III reframed |
| 4. Data & corpus | 1,300-book corpus, join, gold sources, HathiTrust cross-check | Conference §III-C + E1 |
| 5. Acquisition accuracy (RQ2/RQ3) | Panel-validated gold; agreement ceiling; model/conditioning/knowledge-type drivers | Conference RQ4 + new |
| 6. Downstream utility (RQ1) | Gain-vs-coverage at scale; field ablation; robustness | Conference RQ1/RQ5 + E1 |
| 7. Cost of acquisition (RQ4) | E4 panel results: time/edits/quality | New (instrument ready) |
| 8. Synthesis & decision analysis (RQ5) | Utility per expert-hour vs. coverage; break-even | **New** |
| 9. Discussion & limitations | Generalization, query-realism bound, implications | Conference Conclusion expanded |

Length target: 8,000–12,000 words. ≥30% new material is satisfied by E1
scaling, the panel studies (E2/E4), the drivers ablation (E3), the
authority-sourced queries (§5), and the synthesis.

---

## 7. What KBS reviewers will probe (prepare for these)

1. **Knowledge-engineering relevance:** "What does this teach us about
   acquiring knowledge with LLMs, beyond one library application?" — answer
   in the intro and discussion: the field-decomposition result
   (thesaurus vs. classification) is the generalizable claim.
2. **Single-model objection:** deepseek-chat alone is insufficient — the E3
   model comparison is mandatory, not optional.
3. **Gold validity:** one source of gold is not enough — the panel agreement
   ceiling (E2) is the fix; the HathiTrust cross-check helps.
4. **Query realism:** the paraphrase threat (§5 of plan) — authority-sourced
   queries; a KBS reviewer will spot the circularity immediately.
5. **Relevance-judge credibility:** answered by the human-calibration pilot
   (κ human–LLM 0.64–0.80 vs human–human 0.755); extend to the new queries.
6. **Baseline fairness:** retrieval components are deliberately standard —
   state this explicitly so the contribution is read as the knowledge
   analysis, not a new retriever.

---

## 8. First actions (checklist)

- [ ] Verify KBS SCIE status + current JIF on the Clarivate Master Journal List
- [ ] Read the [KBS guide for authors](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors)
- [ ] Start cataloger-panel recruitment (`phase1/outreach_catalogers.md`; E4 instrument ready)
- [ ] Choose title (#1 or #3) and lock the knowledge-acquisition framing
- [ ] Begin E1 corpus scale-up and E3 model comparison (compute/API)
