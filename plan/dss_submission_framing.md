# DSS Submission Framing — Decision Support Systems (Elsevier)

**Date:** 2026-09-05
**Source material:** AIDL 2026 conference paper (*Filling the Gaps: When LLM
Cataloging Improves Library Discovery*, `paper/main.tex`, 8 pp.) + the
retargeted extension plan (`plan/extended_journal_paper.md`).
**Venue:** *Decision Support Systems* — SCIE, IF ≈ 6.8 (Q1). Verify on the
Clarivate Master Journal List before submitting; confirm JIF and format in the
[guide for authors](https://www.sciencedirect.com/journal/decision-support-systems/publish/guide-for-authors).

---

## 1. How to see this paper the way DSS sees it

DSS publishes research on **decision support**: models, methods, and systems
that help an organization decide. The conference paper was written for a
library-AI audience ("LLM metadata improves discovery"). DSS reviewers are
information-systems/decision-science readers, and they will ask three questions
your conference version does not answer:

1. **What is the decision?** — Whether (and where) a library should invest in
   LLM-generated metadata enrichment.
2. **What does the paper give the decision-maker?** — A gain function
   (discovery benefit per unit of subject-access coverage), a cost function
   (cataloger time per record, drafting vs. verifying), and a break-even /
   decision curve.
3. **Why is the evidence credible?** — Validated gold, inter-cataloger
   agreement ceiling, human-calibrated relevance judgments, released
   code/benchmark/data.

The cataloging/discovery machinery is the **application domain**; the
**contribution is the decision model**. Everything in the conference paper
becomes an input to RQ5.

---

## 2. Working title options

1. *Should We Let an LLM Finish the Catalog? A Decision-Support Analysis of LLM
   Metadata Enrichment for Library Discovery* (question-led; DSS-friendly)
2. *When Does LLM Metadata Enrichment Pay Off? A Cost–Benefit Decision Model
   for Library Subject-Access Investment* (decision-model-led)
3. *Gap-Filling the Catalog: A Decision-Support Study of LLM-Generated Subject
   Metadata and Its Value for Discovery* (mechanism-led)

Recommendation: **#1 or #2**. Avoid the conference title's passive framing
("When LLM Cataloging Improves…"); DSS titles name the decision or the model.

---

## 3. Abstract (target 200–250 words) — draft

> Libraries face a concrete decision: whether to let large language models
> (LLMs) write the subject metadata their discovery systems depend on. Prior
> work shows LLMs can draft subject headings and classifications, and recent
> evidence shows that LLM-generated metadata, indexed where professional
> headings are missing, improves topical retrieval. What libraries lack is a
> way to turn that evidence into an investment decision: the gain is a function
> of their existing subject-access coverage, the cost is cataloger effort, and
> neither has been measured against the other.
>
> We address this with a decision-support analysis of LLM metadata enrichment
> for library discovery. Using a corpus of 1,300 public-domain books and a
> released two-sided benchmark, we (i) estimate the discovery gain of
> enrichment as a function of subject-access coverage — the gain is largest
> where catalogs are thinnest and never reaches zero; (ii) calibrate LLM
> cataloging quality against professional gold and an inter-cataloger
> agreement ceiling, showing the LLM operates near the human agreement bound;
> and (iii) measure the cost side — cataloger time drafting metadata from
> scratch versus verifying LLM drafts — under a counterbalanced panel study.
> We synthesize these into a decision curve: expected discovery gain per
> cataloger-hour as a function of a library's current coverage, with the
> break-even point identified. For the collections studied, LLM enrichment is
> cost-effective precisely in the gap-filling regime — sparse catalogs with
> backlogs of uncataloged or thinly cataloged records — and not as a wholesale
> replacement of professional cataloging. Code, benchmark, and data are
> released for reuse.

---

## 4. Contribution list (what the paper claims, DSS-framed)

1. **A decision model (RQ5):** discovery gain per cataloger-hour of LLM
   metadata enrichment, as a function of subject-access coverage, with the
   break-even coverage identified. This is the first cost-side measurement of
   LLM cataloging we know of; prior work stops at quality or at retrieval gain.
2. **A validated gain function (RQ1, E1):** enrichment benefit vs. coverage,
   estimated on a ~10× larger corpus with bootstrap CIs and a released
   benchmark — the input a manager reads their own catalog against.
3. **Calibrated quality evidence (RQ2–RQ3, E2–E3):** LLM cataloging accuracy
   relative to validated professional gold *and* an inter-cataloger agreement
   ceiling; plus what drives quality (model tier, full-text conditioning,
   vocabulary type), identifying which intervention levers exist.
4. **A measured cost function (RQ4, E4):** cataloger minutes per record —
   drafting vs. verifying LLM drafts — from a counterbalanced panel study.
5. **Open artifacts:** code, benchmark, data, and protocols released; human
   relevance judgments and judge calibration reported.

---

## 5. Positioning paragraph (draft for Related Work / Motivation)

> Metadata enrichment for discovery is a resource-allocation problem, but the
> literature has studied it as two separate quality questions. On the
> generation side, studies show LLMs can assign subject headings and call
> numbers with varying agreement against catalog records, and that evaluation
> is typically single-model and single-source. On the retrieval side, work on
> retrieval-augmented generation and metadata-aware search shows that
> bibliographic metadata — subject headings above all — bounds topical
> discovery quality. Neither line measures the *economics* of the decision:
> what the enrichment gain is worth per unit of cataloging effort, and how the
> answer depends on a library's existing coverage. This paper supplies that
> missing link as a decision model, built from measurements on both sides and
> calibrated against professional judgment.

---

## 6. Structure map: conference paper → DSS manuscript

| DSS manuscript section | Content | Source |
|---|---|---|
| 1. Introduction | Decision context; gap; contributions (DSS-framed, §4) | Conference §I rewritten |
| 2. Related work | Two strands + "no cost-side/decision work" position | Conference §II, rewritten to IS/DSS voice, comparison table added |
| 3. Decision model & method | Formalize gain/cost/break-even; system (META-RAG), benchmark (LIBRA-Eval) as measurement apparatus | Conference §III reframed |
| 4. Data & corpus | 1,300-book corpus, join, gold sources, HathiTrust cross-check | Conference §III-C + E1 |
| 5. Experiments | RQ1 gain-vs-coverage (sparsity sweep at scale); RQ2 panel-validated quality; RQ3 drivers; RQ4 cost | Conference RQ1/RQ4/RQ5 + new panel/model/conditioning work |
| 6. Decision analysis (RQ5) | Decision curve, break-even, sensitivity to coverage & cost assumptions | **New** — the DSS core |
| 7. Robustness & validity | Bootstrap CIs, pooled graded + human-calibrated relevance, judge calibration, authority-sourced queries (§5 of plan) | Conference §V-G + new |
| 8. Discussion & implications | What a collection manager does with the curve; limits; future work | Conference Conclusion expanded |
| 9. Conclusion | Contributions restated as decision support | Conference Conclusion |

Length target: 8,000–12,000 words (DSS norm). ≥30% new material over the
proceedings version is satisfied by the decision analysis (RQ5), the panel
studies (E2/E4), the scaling (E1), the drivers ablation (E3), and the
authority-sourced query fix.

---

## 7. What DSS reviewers will probe (prepare for these)

1. **Decision relevance:** "Who is the decision-maker and what exactly do they
   decide differently after reading this?" — answer in the intro and again in
   the decision-analysis section.
2. **Cost validity:** time-per-record from N≈40 per cataloger is thin — report
   per-cataloger variance, pre-register the analysis, and be explicit about
   what the small-n cost estimate can and cannot support.
3. **Generalizability:** one LLM, one language, public-domain literature —
   the model-tier comparison (E3) and the coverage sweep are your defense;
   keep the "within studied collections" scoping from the conference version.
4. **Query realism:** the paraphrase threat (§5 of plan) — authority-sourced
   queries are the fix; do not submit without it.
5. **Relevance-judge credibility:** now answered by the human-calibration pilot
   (κ human–LLM 0.64–0.80 vs human–human 0.755); extend it to the new
   authority-sourced queries.
6. **Benchmark credibility:** LIBRA-Eval two-sided, released, human-validated
   gold, HathiTrust cross-check — this is your strongest card; lead with it in
   the methods.

---

## 8. First actions (checklist)

- [ ] Verify DSS SCIE status + current JIF on the Clarivate Master Journal List
- [ ] Read the [DSS guide for authors](https://www.sciencedirect.com/journal/decision-support-systems/publish/guide-for-authors) (format, length, reference style)
- [ ] Start cataloger-panel recruitment (critical path; `phase1/outreach_catalogers.md`)
- [ ] Decide panel fallback trigger date (plan §7)
- [ ] Choose title (#1 or #2) and lock the decision-model framing
- [ ] Begin E1 corpus scale-up (compute only)
