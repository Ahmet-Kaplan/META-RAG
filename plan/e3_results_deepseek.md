# E3 results — DeepSeek cells (run 2026-09-10)

Spec: `plan/e3_model_comparison.md`. Orchestrator: `phase1/scripts/run_e3.py`.
Artifacts: `phase1/data/e3/`, `phase1/reports/e3/`,
`phase1/reports/e3_scores.{json,md}`.

## What ran

| Cell | Records | Notes |
|---|---|---|
| `deepseek-chat` × sparse (anchor) | 591 scored (600 predicted) | The shipped conference run, re-scored with per-record output. Identical prompt/model/temperature, so it is the legitimate sparse anchor without re-calling the API. |
| `deepseek-chat` × full-text | 407 scored (416 predicted, 7 API failures, 177 skipped) | New run: same prompt plus a 1,500-char head-of-text excerpt. Skipped records are those whose Gutenberg text was not in the cache at run time (mirror-404 works that need the slow endpoint). |

Clean-up: text excerpts for 414/598 records were cached during this session;
the remaining ~184 need a slower download path and can be topped up later
(the cache is resumable; the cell can then be re-run with `--resume`).

## Headline numbers

### Cell-level (different record sets — for orientation only)

| cell | n | LCSH exact | LCSH any-level | DDC class3 | authority violations |
|---|---|---|---|---|---|
| sparse | 600 | 0.342 | 0.633 | 0.828 | 20/1881 (1.06%) |
| full-text | 416 | **0.447** | **0.735** | **0.859** | 19/1495 (1.27%) |

### H2 — strict paired test (the claim)

On the **191 records that carry both a subject-heading score and a gold-DDC
score in both cells** (the only strictly paired comparison available):

| Metric | sparse | full-text | Δ |
|---|---|---|---|
| LCSH any-level | 0.776 | 0.837 | **+0.061** |
| DDC 3-digit class | 0.838 | 0.853 | **+0.016** |

**Difference-of-differences = +0.045, 95% CI [−0.004, +0.095]** → the
direction supports H2 (full text helps thesaurus-style subject acquisition
more than hierarchical classification), but the interval **touches zero**:
at this sample size the interaction is suggestive, not resolved.

An earlier version of the orchestrator compared the LCSH delta over all 407
text-bearing records against the DDC delta over the gold-DDC subset. That is
not paired and overstated the interaction (+0.098 vs +0.016, CI
[+0.046, +0.114]). The strict test above is now the primary one; the loose
variant is retained in `e3_scores.json` for transparency. **This is the
single most important methodological note in this file.**

### H3 — representation gap

The LCSH-vs-DDC gap holds in both cells (sparse gap 0.117; full-text gap
0.038 — the gap *narrows* under full text, consistent with H2).

### Secondary observation

Fabrication does not increase with content conditioning: authority
violations are 1.06% of predicted headings in the sparse cell and 1.27% in
the full-text cell.

## What these results do and do not support

**Supported:** full-text conditioning improves LLM subject cataloging
materially (LCSH any-level +6.1 points on the paired set, +10.2 points
cell-level), with a smaller and more uncertain effect on classification —
the predicted mechanism for why the thesaurus representation carries the
downstream utility and the hierarchy does not. Fabrication stays flat.

**Not yet supported:** the H2 interaction as a *resolved* claim. n=191
paired records is underpowered; the CI includes zero. Two fixes, both
already specified: (i) add the frontier and open/small tiers (E3 multi-model
cells) — more cells give the interaction more evidence and test H3's
robustness; (ii) top up the text cache so the paired set grows toward the
~204 gold-DDC records and the wider text subset.

## Next actions

1. Top up the remaining ~184 text excerpts (resumable; slow endpoint).
2. Re-run the full-text cell with `--resume` to extend the paired set.
3. Add model tiers: `run_e3.py --models deepseek:deepseek-chat,gemini:gemini-3.1-pro-preview,openai_compatible:<local>` — blocked on Gemini credits and/or a local GPU.
4. Re-run `run_e3.py --score-only` after any new cell to refresh the table
   and tests (scoring is offline-safe with `--no-authority` if id.loc.gov
   is unreachable).
