# Enrichment-gain law: does the sparsity curve transfer?

- Fitted on the 227-book collection (1076 questions), validated on the 1011 books of the 1,300-book build that are disjoint from it (6566 questions)
- x = baseline subject-access completeness; r = share of headingless records an LLM prediction exists for; y = topical nDCG@10 gain from enrichment
- Models are fitted on the fit curve only; out-of-sample columns are predictions for a collection no parameter saw

## Measured curves

| Collection | completeness | reachability | base | enriched | gain |
|---|---|---|---|---|---|
| fit | 0.000 | 1.00 | 0.313 | 0.656 | **+0.343** |
| fit | 0.088 | 1.00 | 0.350 | 0.668 | **+0.318** |
| fit | 0.172 | 1.00 | 0.407 | 0.683 | **+0.276** |
| fit | 0.256 | 1.00 | 0.444 | 0.725 | **+0.281** |
| fit | 0.344 | 1.00 | 0.489 | 0.740 | **+0.251** |
| fit | 0.432 | 1.00 | 0.546 | 0.760 | **+0.214** |
| fit | 0.515 | 1.00 | 0.594 | 0.783 | **+0.189** |
| fit | 0.599 | 1.00 | 0.646 | 0.791 | **+0.144** |
| fit | 0.687 | 1.00 | 0.692 | 0.797 | **+0.106** |
| held-out | 0.000 | 0.57 | 0.231 | 0.327 | **+0.096** |
| held-out | 0.096 | 0.58 | 0.266 | 0.357 | **+0.091** |
| held-out | 0.191 | 0.59 | 0.305 | 0.386 | **+0.081** |
| held-out | 0.285 | 0.62 | 0.367 | 0.456 | **+0.089** |
| held-out | 0.379 | 0.66 | 0.409 | 0.489 | **+0.081** |
| held-out | 0.473 | 0.71 | 0.446 | 0.526 | **+0.080** |
| held-out | 0.567 | 0.77 | 0.484 | 0.554 | **+0.070** |
| held-out | 0.658 | 0.87 | 0.526 | 0.583 | **+0.056** |
| held-out | 0.748 | 1.00 | 0.564 | 0.606 | **+0.043** |

## Model fit and transfer

| Model | form | in-sample MAE | out-of-sample MAE | out-of-sample R2 | completeness where gain < 0.02 |
|---|---|---|---|---|---|
| M1 | `g0*(1-x)` | 0.0119 | 0.1456 | -98.597 | 0.944 |
| M2 | `a + b*x` | 0.0109 | 0.1482 | -98.488 | 0.993 |
| M3 | `g0*(1-x)*r` | 0.0119 | 0.0696 | -19.127 | 0.921 |
| M4 | `g0*exp(-k*x)` | 0.0211 | 0.1498 | -103.334 | nan |
