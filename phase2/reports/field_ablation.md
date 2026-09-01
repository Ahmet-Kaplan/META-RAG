# Field ablation: which catalog field carries the signal?

- 227 records, full in-corpus pool (1076 questions), meta mode
- Bootstrap 95% CIs (10,000 resamples); paired permutation vs. `full` (20,000 sign-flips)
- Authors are present in every configuration (identity baseline)

| Fields indexed | known_item | topical | bib_fact | overall | p vs full (topical) |
|---|---|---|---|---|---|
| authors | 0.532 [0.480, 0.582] | 0.063 [0.041, 0.086] | 0.109 [0.083, 0.137] | 0.228 [0.205, 0.251] | 0.0001 |
| title | 0.951 [0.932, 0.968] | 0.313 [0.268, 0.359] | 0.958 [0.945, 0.969] | 0.753 [0.728, 0.777] | 0.0001 |
| subj | 0.585 [0.536, 0.633] | 0.600 [0.550, 0.649] | 0.285 [0.245, 0.327] | 0.478 [0.450, 0.506] | 0.0001 |
| ddc | 0.536 [0.485, 0.587] | 0.066 [0.044, 0.091] | 0.117 [0.090, 0.146] | 0.233 [0.210, 0.257] | 0.0001 |
| title+subj | 0.897 [0.869, 0.922] | 0.691 [0.645, 0.737] | 0.948 [0.932, 0.962] | 0.851 [0.832, 0.870] | 0.0678 |
| title+ddc | 0.943 [0.922, 0.962] | 0.304 [0.259, 0.348] | 0.970 [0.959, 0.980] | 0.752 [0.728, 0.776] | 0.0001 |
| subj+ddc | 0.585 [0.536, 0.633] | 0.595 [0.545, 0.643] | 0.288 [0.248, 0.329] | 0.478 [0.450, 0.505] | 0.0001 |
| full | 0.893 [0.865, 0.918] | 0.686 [0.640, 0.731] | 0.962 [0.949, 0.973] | 0.853 [0.834, 0.871] | -- |

## Marginal contribution of each field

Gain from adding the field to the other two (`full` minus the configuration that drops only it).

| Field | topical gain | 95% CI | p | overall gain |
|---|---|---|---|---|
| subj | **+0.382** | [+0.333, +0.431] | 0.0001 | +0.101 |
| ddc | **-0.005** | [-0.011, +0.000] | 0.0678 | +0.002 |
| title | **+0.091** | [+0.057, +0.127] | 0.0001 | +0.375 |
