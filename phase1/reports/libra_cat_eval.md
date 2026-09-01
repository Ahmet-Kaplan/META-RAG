# LIBRA-CAT evaluation (LLM cataloging)

Model: `deepseek-chat`, temperature 0. Input: title, author, year only
(retrospective-conversion setting). Gold never shown to the model.
Records: 600 · generation failures: 0

## Subject headings — gold recall by scoring level

1405 gold headings across 600 records.

| Level | Count | Cumulative |
|---|---|---|
| exact | 481 | 34.2% |
| semantic equivalence (cos >= 0.75) | 348 | 59.0% |
| acceptable (correct broader heading) | 61 | 63.3% |
| miss | 515 | — |

Records with at least one exactly correct heading: **55.3%**

## Predicted headings — error taxonomy

1881 predicted headings (mean 3.13 per record).
864 matched gold at exact or semantic level (45.9% precision).

| Category | Count | Share of predictions |
|---|---|---|
| matched gold (exact/semantic) | 864 | 45.9% |
| valid LCSH, no gold match | 932 | 49.5% |
| under-specific | 51 | 2.7% |
| over-specific | 14 | 0.7% |
| **authority violation** | **20** | **1.1%** |

Authority validation queries the main heading against the LC *subjects* and
*names* authority files via `id.loc.gov/authorities/{f}/suggest2`
(0 lookup failures). Only the main heading is
looked up: LCSH subdivisions are free-floating, so most valid
heading+subdivision strings have no single pre-coordinated authority record.
Querying the full string reports ~16% violations, nearly all false positives.

## DDC

204 records carry gold DDC (OpenLibrary, MARC 082 aggregation; scored as
any-gold-match).

| Level | Count | Rate |
|---|---|---|
| exact string | 123 | 60.3% |
| 3-digit class (cumulative) | 46 | 82.8% |
| top-level class only | 18 | — |
| wrong branch | 17 | 8.3% |

## Interpretation

1. **Multi-level scoring is load-bearing.** Exact match credits
   34.2%; allowing semantic equivalence and correct broader
   headings reaches 63.3%. Reporting
   exact match alone understates the model by nearly a factor of two.

2. **Classification transfers better than subject analysis.** DDC reaches
   82.8% at the 3-digit class against 34.2%
   exact for LCSH. Dewey is closed and hierarchical, so the model can be
   approximately right; LCSH is open and pre-coordinated, so it usually cannot.

3. **Fabrication is not the binding constraint.** Only
   20/1881 (1.1%)
   predicted headings have a main heading absent from LC authorities. The
   dominant residual is 932 headings that are valid LCSH but
   match no gold heading for that record.

4. **The 932 unmatched headings are NOT reported as errors.**
   The HathiTrust cross-check shows two professional sources share an exact
   heading for only 9 of 34 books, so a heading absent from Gutenberg gold may be
   a legitimate alternative. Separating error from alternative requires the
   cataloger-panel agreement baseline. Until then these figures are **agreement
   with one professional source**, not accuracy.

## Reproduce

```bash
python3 phase1/scripts/eval_libra_cat.py --workers 8
python3 phase1/scripts/score_libra_cat.py
```
