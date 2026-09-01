# Size scaling: is the transfer failure a collection-size effect?

- Nested subsamples of the 1,241-book build; each size is a superset of the one below, so size is the only thing that changes
- Gain = topical nDCG@10 (enriched - baseline) at each completeness level
- Subsamples of one corpus: this isolates size, not cross-library transfer

| N | questions | completeness | base | enriched | gain |
|---|---|---|---|---|---|
| 150 | 996 | 0.00 | 0.387 | 0.642 | **+0.255** |
| 150 | 996 | 0.20 | 0.475 | 0.706 | **+0.230** |
| 150 | 996 | 0.40 | 0.596 | 0.741 | **+0.146** |
| 150 | 996 | 0.60 | 0.693 | 0.795 | **+0.102** |
| 150 | 996 | 0.80 | 0.798 | 0.834 | **+0.036** |
| 300 | 2007 | 0.00 | 0.341 | 0.593 | **+0.253** |
| 300 | 2007 | 0.18 | 0.435 | 0.636 | **+0.201** |
| 300 | 2007 | 0.37 | 0.537 | 0.689 | **+0.152** |
| 300 | 2007 | 0.55 | 0.620 | 0.722 | **+0.102** |
| 300 | 2007 | 0.73 | 0.713 | 0.751 | **+0.037** |
| 600 | 4019 | 0.00 | 0.298 | 0.528 | **+0.230** |
| 600 | 4019 | 0.18 | 0.362 | 0.565 | **+0.204** |
| 600 | 4019 | 0.37 | 0.454 | 0.600 | **+0.146** |
| 600 | 4019 | 0.56 | 0.534 | 0.627 | **+0.093** |
| 600 | 4019 | 0.74 | 0.631 | 0.680 | **+0.049** |
| 1241 | 8046 | 0.00 | 0.237 | 0.438 | **+0.201** |
| 1241 | 8046 | 0.19 | 0.316 | 0.488 | **+0.172** |
| 1241 | 8046 | 0.37 | 0.391 | 0.527 | **+0.136** |
| 1241 | 8046 | 0.56 | 0.479 | 0.564 | **+0.085** |
| 1241 | 8046 | 0.73 | 0.554 | 0.602 | **+0.048** |

## Does the curve factorize? (reference N=150)

One free scale g per size, relating that size's gain curve to the reference curve.

| N | g | MAE | R2 |
|---|---|---|---|
| 300 | 0.958 | 0.0097 | 0.977 |
| 600 | 0.915 | 0.0079 | 0.979 |
| 1241 | 0.802 | 0.0115 | 0.942 |

Fitted `g(N) = 1.988 * N^(-0.126)`.
A negative exponent means the same headings buy less ranking improvement as the catalog grows.
