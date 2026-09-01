# Selective enrichment: does triage beat cataloging everything?

- 227 records, 227 enrichable, full in-corpus pool (1076 questions)
- Catalog fully stripped first; topical nDCG@10 at 0.313, 0.656 when every enrichable record is catalogued (gain +0.343)
- `random` averaged over seeds 1, 2, 3, 4, 5; `oracle` ranks by measured gain and is an upper bound, not a policy

| Policy | 10% (23 calls) | 25% (57 calls) | 50% (114 calls) | 75% (170 calls) |
|---|---|---|---|---|
| random | 0.340 (8% of full gain) | 0.400 (25% of full gain) | 0.483 (49% of full gain) | 0.564 (73% of full gain) |
| title_poverty | 0.362 (14% of full gain) | 0.430 (34% of full gain) | 0.515 (59% of full gain) | 0.602 (84% of full gain) |
| novel_idf | 0.344 (9% of full gain) | 0.415 (30% of full gain) | 0.497 (54% of full gain) | 0.603 (84% of full gain) |
| oracle | 0.425 (33% of full gain) | 0.592 (81% of full gain) | 0.671 (104% of full gain) | 0.663 (102% of full gain) |

## Heuristic vs. random at equal budget (paired, topical questions)

| Policy | budget | delta | 95% CI | p |
|---|---|---|---|---|
| title_poverty | 10% | +0.0206 | [-0.0132, +0.0554] | 0.2496 |
| title_poverty | 25% | +0.0419 | [-0.0007, +0.0861] | 0.0626 |
| title_poverty | 50% | +0.0312 | [-0.0167, +0.0794] | 0.2054 |
| title_poverty | 75% | +0.0202 | [-0.0231, +0.0620] | 0.3482 |
| novel_idf | 10% | +0.0024 | [-0.0254, +0.0309] | 0.8673 |
| novel_idf | 25% | +0.0266 | [-0.0090, +0.0638] | 0.1541 |
| novel_idf | 50% | +0.0137 | [-0.0327, +0.0606] | 0.5689 |
| novel_idf | 75% | +0.0205 | [-0.0162, +0.0578] | 0.2918 |
