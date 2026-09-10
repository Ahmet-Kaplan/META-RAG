# E3 — Multi-Model Acquisition Comparison (KBS journal, RQ3)

**Purpose:** kill the single-model objection. The conference-scale LIBRA-CAT
results rest on one LLM (`deepseek-chat`); a KBS reviewer will reject an
LLM-quality claim from a single model. E3 measures *what drives acquisition
quality* across three factors — model, conditioning, and knowledge
representation — and tests the mechanistic prediction that full-text
conditioning helps thesaurus-style subject acquisition (LCSH) more than
hierarchical classification (DDC).

**Status:** spec. Runs after cataloger-panel recruitment starts (no panel
dependency) and can proceed in parallel with E1.

---

## 1. Objective and hypotheses

| ID | Question | Hypothesis (directional) |
|---|---|---|
| H1 | Does acquisition quality vary across model tiers? | Yes; the gap should be largest on open-vocabulary LCSH, smallest on closed DDC |
| H2 | Does full-text conditioning improve acquisition? | Yes overall, but **more for LCSH than DDC** (mechanism: content helps choose among open heading strings; closed classes are less content-sensitive) |
| H3 | Is the representation gap (LCSH ≪ DDC) robust across models and conditions? | Yes — it is structural (open vs. closed vocabulary), not a single-model artifact |

H2 is the headline mechanistic claim that would *explain* the LCSH/DDC gap
rather than describe it; H3 protects the conference paper's central
representation-dependence result against the single-model objection.

---

## 2. Factor design

| Factor | Levels | Notes |
|---|---|---|
| **Model** | 3: frontier, mid (baseline = `deepseek-chat`), small/open | Model roster in §3 |
| **Conditioning** | 2: sparse (title/author/year) vs. full-text (title/author/year + text excerpt) | Sparse = exactly the shipped protocol; full-text adds a head-of-text excerpt |
| **Representation** | 2: LCSH headings vs. DDC | Not a run factor — it is the two output fields, scored separately |

Full design is **Model (3) × Conditioning (2)** = 6 run cells, each scored
on LCSH and DDC separately.

---

## 3. Model roster

Verified facts from the environment:

| Tier | Model | Endpoint | Key | Status (verified 2026-09-05) |
|---|---|---|---|---|
| Frontier | `gemini-3.1-pro-preview` (or `gemini-2.5-flash`) | OpenAI-compatible `generativelanguage.googleapis.com/v1beta/openai/` | `GEMINI_API_KEY` set | **Client path verified working** (auth accepted). Two live findings: (i) `gemini-2.5-pro` is RETIRED — use `gemini-3.1-pro-preview`; (ii) the key currently returns 429 "prepayment credits are depleted", so the account must be topped up before this tier can run |
| Mid (baseline) | `deepseek-chat` | `api.deepseek.com` | `DEEPSEEK_API_KEY` set | Shipped results exist (600 records) — the anchor cell; live call verified |
| Small/open | Local open-weight (e.g., Qwen2.5-7B / Llama-3.1-8B) **or** `deepseek-reasoner` as fallback | local vLLM/Ollama, or DeepSeek | — | Needs a GPU machine; if unavailable, substitute `deepseek-reasoner` and disclose the substitution |

**Client (IMPLEMENTED — Option A):** `phase1/scripts/llm_client.py` now
resolves a provider per call (`deepseek` | `gemini` | `openai_compatible`),
with `model=`/`provider=` arguments and `*_MODEL`/`*_BASE_URL` env overrides;
existing call sites keep their DeepSeek behaviour unchanged. Verified live:
DeepSeek call OK; Gemini auth+endpoint OK (billing blocked, see above).

The small/open tier's local model is the honest "open-weight" claim; if no
GPU is available, disclose the `deepseek-reasoner` substitution rather than
dropping the tier.

---

## 4. Protocol (prompting)

**Sparse condition** — reuse the shipped prompt verbatim
(`phase1/scripts/eval_libra_cat.py`, `SYSTEM` + `PROMPT`): title/author/year
only, `temperature=0.0`, LCSH + DDC JSON output. This keeps the mid/sparse
cell exactly comparable to the shipped 600-record run.

**Full-text condition** — the same prompt plus a `Content` block:

```text
Content excerpt (for cataloging context):
{excerpt}
```

Excerpt = first ~1,500 characters of the work's Gutenberg text after the
Project Gutenberg header boilerplate, cleaned of the license preamble.
Download from `plaintext_url` reusing `phase2/scripts/corpus.py`'s
`download_text()` (598/600 records carry a URL); cache per work_key so each
record downloads once across all model cells. Strip the PG header
(detect the `*** START OF THE PROJECT GUTENBERG EBOOK` marker) so the model
sees the work, not the license.

Gold is never shown; identical system prompt and temperature across all
cells.

---

## 5. Sample

| Cell | Records | Why |
|---|---|---|
| Sparse × 3 models | all 600 | Full pool; mid/sparse is the shipped anchor (already run) |
| Full-text × 3 models | all 600 (text fetchable) | Full pool; download is cached, cost is the API calls |

No subsampling needed at 600 records × 6 cells = 3,600 catalog calls
(~$2–10 total at API rates; see §8). Records are the paired sampling unit:
every record appears in all 6 cells, so model/condition comparisons are
within-record (paired), the strongest design available.

---

## 6. Scoring and outputs

Reuse the shipped scoring (`phase1/scripts/score_libra_cat.py`) per cell,
with the authority cache so no re-querying of `id.loc.gov`:

| Metric | Definition |
|---|---|
| LCSH gold coverage | exact / +semantic / +acceptable (multi-level rubric) |
| DDC accuracy | exact string, 3-digit class, wrong-branch |
| Fabrication rate | % predicted headings absent from LC authorities (cache) |
| Error taxonomy | over/under-specific, valid-but-unmatched shares |

Outputs (mirroring repo conventions — JSON + .md, machine-generated):
- `phase1/data/e3/preds_{model}_{sparse|fulltext}.jsonl` (one row per record)
- `phase1/reports/e3_scores.json` / `.md` — per-cell table with bootstrap CIs
- `phase1/reports/e3_interaction.md` — the H2/H3 test results

The E3 table replaces the single-model LIBRA-CAT column in
`plan/kbs_valid.tex` §5.3 (the "model and conditioning" TODO).

---

## 7. Statistical analysis

- **H1 (model effect):** per-record paired comparison; report per-model
  LCSH-any-level and DDC-class3 with bootstrap CIs. Since records repeat
  across cells, model differences are within-record.
- **H2 (conditioning × representation interaction):** the headline test.
  Per record, compute Δ(full-text − sparse) for LCSH-any-level and for
  DDC-class3; test whether the LCSH Δ exceeds the DDC Δ (paired, e.g.,
  permutation test on the difference of differences). A positive result is
  the mechanistic explanation of the representation gap.
- **H3 (robustness):** the conference result — LCSH ≪ DDC — must hold in all
  6 cells; report the gap per cell with CIs rather than as a point claim.
- Pre-register the analysis (directions in §1) before running; report all
  cells, including failures.

---

## 8. Cost and runtime

| Item | Estimate |
|---|---|
| DeepSeek sparse (anchor) | done (shipped run) |
| Gemini frontier, 2 conditions × 600 | ~1,200 calls; flash tier ~$0.1–0.5, pro tier higher — check current pricing |
| DeepSeek full-text cell | ~600 calls × ~1,200 tokens ≈ well under $1 |
| Small/open local | GPU machine time (~hours), or `deepseek-reasoner` API |
| Text downloads | 598 × ~0.5 MB, cached; Gutenberg rate limits — run on user's network if datacenter IP is blocked |

Workers: reuse the `--workers 8` threaded pattern in `eval_libra_cat.py`.
Resume support (`--resume`) so an interrupted cell continues.

---

## 9. Code changes required

1. `phase1/scripts/llm_client.py` — provider abstraction (Option A above).
2. `phase1/scripts/eval_libra_cat.py` — add `--model`, `--condition
   {sparse,fulltext}`, `--text-cache`; full-text prompt variant; out path
   per cell.
3. New `phase1/scripts/run_e3.py` — orchestrates the 6 cells, downloads +
   caches text once, calls the scorer per cell, emits the report tables.
4. `phase1/scripts/score_libra_cat.py` — already reusable; confirm it
   accepts an arbitrary predictions file (it does: `--preds`).

No change to the retrieval/evaluation pipeline — E3 touches only the
acquisition component and its scoring.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Gemini client not built | Option A is ~20 lines; test with 1 record before the run |
| No GPU for the open-weight tier | Disclose `deepseek-reasoner` substitution; keep the tier's purpose (cost/quality spread) explicit |
| Gutenberg rate-limits datacenter IP | Run text download on the user's network (corpus.py already notes this); cache is resumable |
| API drift (unversioned model endpoints) | Pin model snapshot names and dates in the report, per the paper's reproducibility stance |
| H2 null (full text does not help LCSH more) | A null is publishable: it would mean the LCSH/DDC gap is not conditioning-driven, narrowing the mechanism; report honestly |

---

## 11. Decision points for the author

1. **Frontier model:** Gemini 2.5 Pro vs. Flash — Pro is the honest
   "frontier" claim; Flash is cheaper. Recommend Pro if the API budget
   allows.
2. **Open tier:** is a GPU machine available, or substitute
   `deepseek-reasoner`?
3. **Client refactor:** Option A (extend `llm_client.py`) vs. Option B
   (separate Gemini client) — recommend A.
4. Run E3 before or alongside E1 — no dependency either way (E3 uses the
   600-record LIBRA-CAT pool; E1 scales the retrieval corpus).
