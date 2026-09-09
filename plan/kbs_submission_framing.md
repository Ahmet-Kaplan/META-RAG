# KBS Submission Framing — Knowledge Engineering Emphasis

**Date:** 2026-09-05 (rev. 2 — knowledge-engineering framing emphasized)
**Source material:** AIDL 2026 conference paper (*Filling the Gaps: When LLM
Cataloging Improves Library Discovery*, `paper/main.tex`, 8 pp.) + the
retargeted extension plan (`plan/extended_journal_paper.md`).
**Venue:** *Knowledge-Based Systems* — SCIE (Computer Science – Artificial
Intelligence), Q1, IF ≈ 7–8.8 (2023 JCR). Verify current JIF and format on the
Clarivate Master Journal List and the [KBS guide for authors](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors).

---

## 1. The knowledge-engineering view of this paper

KBS publishes knowledge-based systems research: how knowledge is **acquired,
represented, validated, and used** by systems that perform tasks. Read that
way, this paper is a knowledge-engineering study whose application domain is
library discovery. Every component of the work is already a KE artifact; the
task of the journal version is to say so in KE vocabulary and to generalize the
results beyond the library.

| KE problem class | What the paper does | Paper element |
|---|---|---|
| **Knowledge acquisition** | An LLM acquires subject knowledge (LCSH headings, DDC classes) from sparse input (title/author/year), in the retrospective-conversion setting | LIBRA-CAT generation (RQ2/RQ4 in conference terms) |
| **Knowledge representation** | Two canonical representations compared: pre-coordinated thesaurus strings (LCSH) vs. a closed hierarchical taxonomy (DDC) | Vocabulary-type comparison — LCSH exact 34.2% vs. DDC 3-digit 82.8% |
| **Knowledge validation** | Acquired knowledge checked against professional gold, multi-level (exact/semantic/acceptable), live authority checking (id.loc.gov), and an inter-cataloger agreement ceiling | LIBRA-CAT scoring + error taxonomy + panel (E2) |
| **Knowledge utilization in a KBS** | A consuming knowledge-based system (metadata-aware retrieval index) is the test of knowledge utility: which knowledge fields it consumes, how utility varies with knowledge-base completeness | Field ablation (+0.382 topical nDCG@10 for subjects, DDC ≈ 0), sparsity sweep (RQ1/RQ5) |
| **Knowledge-base completeness** | Utility of adding missing knowledge where the KB has gaps — the gain is largest at lowest coverage and never reaches zero | Gap-filling / sparsity results |
| **Knowledge quality taxonomy** | Acquired knowledge classified into error types (invented, over-/under-specific, authority violations, valid-but-unmatched) and a decomposition of the residual | Error taxonomy + unmatched-heading decomposition |

**The one-line KE claim:** *LLM-generated subject knowledge is a viable
acquisition channel for a knowledge-based retrieval system, but its utility is
representation-dependent and coverage-dependent — the open, pre-coordinated
thesaurus representation carries the entire downstream effect, the closed
hierarchical classification carries none, and the value concentrates in the
low-completeness regime.*

---

## 2. Working titles (knowledge-engineering led)

1. *Knowledge Acquisition by LLMs: The Value of Machine-Acquired Subject
   Knowledge for Knowledge-Based Retrieval* (KE-generic; library is the testbed)
2. *Acquiring, Validating, and Deploying LLM-Generated Knowledge in a
   Knowledge-Based Retrieval System: A Subject-Headings Case Study*
3. *What Is Acquired Knowledge Worth? A Knowledge-Engineering Study of
   LLM-Acquired Subject Metadata for Retrieval*
4. *LLMs as Knowledge-Acquisition Components: Representation-Dependent Utility
   of Machine-Acquired Subject Knowledge*

Recommendation: **#1** (generalizes, leads with the KE construct) with #4 as a
strong alternative that foregrounds the representation-dependence finding.
Avoid titles that lead with "cataloging" or "libraries".

---

## 3. Abstract (target 200–250 words) — KE-emphasized draft

> Knowledge-based systems depend on knowledge that is expensive to acquire and
> unevenly distributed: in knowledge-based retrieval, the structured subject
> knowledge that describes what documents are about is missing for many
> documents. Large language models (LLMs) promise a cheap acquisition channel —
> they can propose subject knowledge from minimal input — but the
> knowledge-engineering questions are whether the acquired knowledge is valid,
> which representation of it a consuming system actually uses, and what
> acquisition costs. We study these questions in a controlled corpus of 1,300
> documents with professionally validated ground truth and a released two-sided
> benchmark. An LLM knowledge-acquisition component produces subject knowledge
> in two canonical representations — open, pre-coordinated thesaurus strings
> (LCSH headings) and a closed hierarchical classification (DDC). We evaluate
> acquisition validity against professional gold with a multi-level rubric and
> live authority checking, and we evaluate knowledge utility by feeding the
> acquired knowledge into a knowledge-based retrieval index and measuring
> retrieval quality as a function of representation and knowledge-base
> completeness. Three findings. First, the utility of machine-acquired subject
> knowledge is representation-dependent: the thesaurus representation carries
> the entire downstream gain (+0.382 topical nDCG@10; 95% CI [+0.333, +0.431])
> while the hierarchical classification contributes none, and we explain the
> mechanism (open vs. closed vocabularies). Second, utility is
> completeness-dependent: the gain is largest where the knowledge base is
> sparsest and never reaches zero. Third, acquisition validity is close to the
> human agreement ceiling when measured against validated professional
> knowledge. We close with a cost analysis of machine- vs. expert-acquired
> knowledge and a deployment analysis for knowledge managers. Code, benchmark,
> and data are released.

---

## 4. Contribution list — each mapped to a KE contribution

1. **A complete acquisition-to-utilization evaluation protocol (KE
   methodology):** LLM-acquired knowledge is taken through the full KE cycle —
   acquire from sparse input, validate against multi-level professional gold
   with live authority checking, and measure utility in a consuming KBS — so
   acquisition quality is reported as *what it does to the system that uses
   it*, not as isolated agreement.
2. **Representation-dependent utility (KE finding, generalizable):** the same
   acquisition channel evaluated on two knowledge representations shows that
   downstream utility is carried entirely by the open pre-coordinated thesaurus
   representation (subjects: +0.382 topical nDCG@10, CI [+0.333, +0.431]) and
   not at all by the closed hierarchical one (DDC: −0.005, CI [−0.011,
   +0.000]) — a result about *which knowledge representation to acquire for a
   retrieval task*, with implications beyond libraries.
3. **Completeness-dependent value (KE finding):** machine-acquired knowledge is
   most valuable exactly where the knowledge base has gaps — utility falls
   monotonically with coverage but never reaches zero — giving a
   principled answer to "which knowledge to acquire first."
4. **Validated acquisition accuracy (KE validation):** LLM-acquired subject
   knowledge scored against validated professional gold and an inter-cataloger
   agreement ceiling, with a full knowledge-quality error taxonomy
   (invented / over- / under-specific / authority-violating / valid-but-
   unmatched) and a decomposition of the residual.
5. **Cost of machine- vs. expert-acquired knowledge (KE economics):** expert
   time to acquire the same knowledge from scratch vs. verifying the LLM
   output, from a counterbalanced panel study.
6. **Open artifacts:** code, benchmark, data, and protocols released, with
   human-calibrated relevance judgments.

---

## 5. Positioning paragraph (KE voice, for the Introduction)

> The knowledge-acquisition bottleneck is the classic obstacle of
> knowledge-based systems: the knowledge that lets a system perform a task is
> costly and slow for experts to encode. Large language models offer a new
> acquisition channel, but the knowledge-engineering literature evaluates
> machine-acquired knowledge in isolation — agreement against a single
> reference — or not at all. Three questions go unanswered. Is the acquired
> knowledge valid against professional consensus, not one source? Which
> knowledge representation does the consuming system actually use, so that
> acquisition effort targets the load-bearing representation? And what is the
> knowledge worth as a function of how complete the knowledge base already is?
> We answer all three in a controlled setting: an LLM acquires subject
> knowledge for 1,300 documents, we validate it against professional gold with
> an agreement ceiling, and we measure its utility in a knowledge-based
> retrieval index that consumes it. The domain is bibliographic subject
> knowledge — sparse, expensive, and unevenly distributed — but the object of
> study is the acquisition channel itself: whether LLM-acquired knowledge can
> be validated, which representation carries its utility, and where it pays
> off.

---

## 6. Structure map (KE-emphasized manuscript)

| Section | KE content | Source |
|---|---|---|
| 1. Introduction | Acquisition bottleneck; three KE questions; contributions | Conference §I rewritten |
| 2. Related work | KE-cycle organization (acquisition/representation/validation/utilization) + systematic comparison table (tab:rel) | Draft: `plan/kbs_related_work.tex` |
| 3. Knowledge & system model | Knowledge being acquired (two representations + completeness); acquisition component; consuming KBS (record index + field ablation); measurement apparatus (two-sided benchmark, multi-level rubric, pooled graded) | Draft: `plan/kbs_method.tex` |
| 4. Corpus & ground truth | Corpus (Gutenberg+OL join, chunks); gold KB (LCSH + DDC, any-gold-match); HathiTrust gold validation (inter-source agreement motivates multi-level rubric); released benchmark instruments | Draft: `plan/kbs_data.tex` |
| 5. Validation of acquired knowledge (E2/E3) | Multi-level agreement (exact/semantic/acceptable); error taxonomy + unmatched-residual decomposition (158/241/335, 36.8% union, 589 residual); representation-type + memorization drivers; agreement-ceiling reading | Draft: `plan/kbs_valid.tex` (+ `plan/kbs_unmatched_numbers.tex`) |
| 6. Utility of acquired knowledge (RQ1) | Field ablation (representation dependence: subjects +0.382 vs DDC ~0); coverage sweep (completeness dependence: monotone-decreasing, never zero); robustness; pooled graded + human calibration | Draft: `plan/kbs_util.tex` |
| 7. Cost of acquisition (RQ4) | Counterbalanced panel: manual vs. verify time/edits/quality | Draft: `plan/kbs_cost.tex` (instrument ready; results \TODO E4) |
| 8. Deployment analysis (RQ5) | Decision model G(c)/t; three structural readings (lowest-coverage regime, near-final drafts, representation targeting); caveats | Draft: `plan/kbs_synth.tex` |
| 9. Discussion & limitations | Three claims restated; what transfers vs. not; query-realism/gold/model/cost limits; ethics; future work | Draft: `plan/kbs_disc.tex` |

---

## 7. What KBS reviewers will probe

1. **"Why is this knowledge engineering, not library science?"** — every result
   must be stated at the KE level (representation dependence, completeness
   dependence, validation against consensus) with the library as the case.
2. **The representation-dependence claim** is the generalizable jewel — defend
   it as the headline, with the mechanistic explanation (open pre-coordinated
   vs. closed hierarchical vocabularies) rather than as an aside.
3. **Single-model objection** — deepseek-chat alone is insufficient; E3 model
   comparison mandatory.
4. **Gold validity** — one source of gold is not enough; panel agreement
   ceiling (E2) + HathiTrust cross-check are the fix.
5. **Query circularity** — topical queries paraphrased from the same headings
   being tested; authority-sourced queries (§5 of plan) required.
6. **Relevance-judge credibility** — human-calibration pilot (κ human–LLM
   0.64–0.80 vs human–human 0.755) reported; extend to new queries.
7. **Baseline honesty** — retrieval machinery deliberately standard (BM25F +
   dense twin + RRF); the contribution is the knowledge analysis, not a new
   retriever.
8. **KE literature engagement** — cite the acquisition-bottleneck, ontology /
   thesaurus-representation, and knowledge-validation literatures properly
   (verify every reference programmatically before submission).

---

## 8. First actions

- [ ] Verify KBS SCIE status + current JIF on the Clarivate Master Journal List
- [ ] Read the [KBS guide for authors](https://www.sciencedirect.com/journal/knowledge-based-systems/publish/guide-for-authors)
- [ ] Lock title (#1 or #4) and the KE contribution statements (§4)
- [ ] Run the KE-literature citation pass (acquisition bottleneck, representation,
      validation, KB completeness) — verify all references
- [ ] Start cataloger-panel recruitment (`phase1/outreach_catalogers.md`; E4
      instrument ready) and E3 model comparison
