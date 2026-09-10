# E3 — multi-model acquisition comparison

| cell | provider | model | condition | n | LCSH any-level | DDC class3 | gap |
|---|---|---|---|---|---|---|---|
| deepseek__deepseek-chat__sparse | deepseek | deepseek-chat | sparse | 591 | 0.704 | 0.821 | 0.117 |
| deepseek__deepseek-chat__fulltext | deepseek | deepseek-chat | fulltext | 407 | 0.816 | 0.853 | 0.038 |

## Hypothesis tests

### H2_deepseek
```json
{
 "design": "strict paired (records where both metrics are defined)",
 "n_paired": 191,
 "n_text_subset": 407,
 "lcsh_any_level": {
  "sparse": 0.7759,
  "fulltext": 0.8369,
  "delta": 0.061
 },
 "ddc_class3": {
  "sparse": 0.8377,
  "fulltext": 0.8534,
  "delta": 0.0157
 },
 "diff_of_diff": 0.0453,
 "diff_of_diff_ci95": [
  -0.0038,
  0.0946
 ],
 "supports_H2": false,
 "note": "CI touching zero means the direction is supported but the interaction is not resolved at this sample size; more models/records (E3 multi-model) are needed",
 "loose_variant_unpaired": {
  "n_lcsh": 407,
  "delta_lcsh": 0.0978,
  "n_ddc": 191,
  "delta_ddc": 0.0157,
  "diff_of_diff": 0.0821
 }
}
```
### H3
```json
{
 "cells": [
  {
   "cell": "deepseek__deepseek-chat__sparse",
   "gap": 0.117,
   "holds": true
  },
  {
   "cell": "deepseek__deepseek-chat__fulltext",
   "gap": 0.038,
   "holds": true
  }
 ],
 "holds_in_all_cells": true
}
```
