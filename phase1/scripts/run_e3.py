#!/usr/bin/env python3
"""
run_e3.py — Orchestrate the E3 multi-model acquisition comparison.

Spec: plan/e3_model_comparison.md. Design: Model x Conditioning cells over the
LIBRA-CAT records, each scored with the shipped multi-level rubric, then
aggregated into the report table and the hypothesis tests:

  H1  acquisition quality varies across model tiers
  H2  full-text conditioning helps LCSH MORE than DDC (the mechanistic
      headline; tested as a paired difference-of-differences)
  H3  the LCSH-vs-DDC representation gap holds in every cell

Each cell runs as a subprocess of the shipped scripts, so the E3 results are
produced by exactly the same code path as the conference numbers:

  eval_libra_cat.py --provider P --model M --condition C --out <cell>.jsonl
  score_libra_cat.py --preds <cell>.jsonl --out <cell>_scores \
                     --per-record-out <cell>_per_record.json

Outputs:
  phase1/data/e3/preds_<provider>_<condition>.jsonl      predictions per cell
  phase1/reports/e3/<cell>_scores.json                   aggregate scores
  phase1/reports/e3/<cell>_per_record.json               per-record scores
  phase1/reports/e3_scores.json / .md                    combined table + tests

Usage:
  # plan only, no API calls:
  python3 phase1/scripts/run_e3.py --dry-run

  # baseline cell already shipped; run the new ones:
  python3 phase1/scripts/run_e3.py \
      --models deepseek:deepseek-chat,gemini:gemini-2.5-pro \
      --conditions sparse,fulltext --resume
"""

import argparse
import json
import random
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DEFAULT_MODELS = "deepseek:deepseek-chat"
DEFAULT_CONDITIONS = "sparse,fulltext"


def parse_models(spec: str) -> List[Dict[str, str]]:
    out = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            provider, model = item.split(":", 1)
        else:
            provider, model = item, ""
        out.append({"provider": provider.strip(), "model": model.strip()})
    return out


def cell_tag(cell: Dict[str, str]) -> str:
    m = cell["model"].replace("/", "-").replace(":", "-") or "default"
    return f"{cell['provider']}__{m}__{cell['condition']}"


def run(cmd: List[str], dry: bool) -> int:
    print("  $", " ".join(cmd))
    if dry:
        return 0
    return subprocess.call(cmd)


def kappa_free_report(cells: List[Dict], per_record: Dict[str, Dict],
                      reports_dir: Path, dry: bool) -> Dict:
    """Aggregate cells into the report table and run H1/H2/H3 tests."""
    import numpy as np

    def vec(tag: str, key: str, records: List[str]):
        pr = per_record.get(tag, {})
        return np.array([pr[r][key] for r in records if r in pr and pr[r].get(key) is not None],
                        dtype=float)

    table = []
    for c in cells:
        tag = c["tag"]
        pr = per_record.get(tag, {})
        if not pr:
            continue
        any_lv = [v["any_level"] for v in pr.values()]
        ddc = [v["ddc_ok"] for v in pr.values() if v.get("ddc_ok") is not None]
        table.append({
            "cell": tag, "provider": c["provider"], "model": c["model"],
            "condition": c["condition"], "n": len(pr),
            "lcsh_any_level": round(statistics.mean(any_lv), 3),
            "ddc_class3": round(statistics.mean(ddc), 3) if ddc else None,
            "gap": round(statistics.mean(ddc) - statistics.mean(any_lv), 3) if ddc else None,
        })

    result = {"cells": table, "tests": {}}

    # H2: difference-of-differences (fulltext - sparse), LCSH vs DDC.
    #
    # The strict paired design restricts to records where BOTH metrics are
    # defined in both cells (gold-DDC records), so the two deltas are computed
    # on the same works. An earlier version compared the LCSH delta over all
    # text-bearing records against the DDC delta over the gold-DDC subset;
    # that is not paired and it materially overstated the interaction (it
    # compared +0.098 vs +0.016, whereas the paired estimate is +0.061 vs
    # +0.016). We report the strict test as primary and the loose variant for
    # transparency.
    for prov in sorted({c["provider"] for c in cells}):
        sp = next((c for c in cells if c["provider"] == prov and c["condition"] == "sparse"), None)
        ft = next((c for c in cells if c["provider"] == prov and c["condition"] == "fulltext"), None)
        if not (sp and ft):
            continue
        sp_pr, ft_pr = per_record.get(sp["tag"], {}), per_record.get(ft["tag"], {})
        common = sorted(set(sp_pr) & set(ft_pr))
        strict = [r for r in common
                  if sp_pr[r].get("ddc_ok") is not None
                  and ft_pr[r].get("ddc_ok") is not None]
        if len(strict) < 20:
            continue
        dl = np.array([ft_pr[r]["any_level"] - sp_pr[r]["any_level"] for r in strict])
        dd = np.array([ft_pr[r]["ddc_ok"] - sp_pr[r]["ddc_ok"] for r in strict])
        rng = random.Random(11)
        boot = []
        n = len(strict)
        for _ in range(5000):
            idx = [rng.randrange(n) for _ in range(n)]
            boot.append(dl[idx].mean() - dd[idx].mean())
        lo, hi = np.percentile(boot, [2.5, 97.5])

        # loose variant (reported for reference only)
        d_l_all = np.array([ft_pr[r]["any_level"] - sp_pr[r]["any_level"] for r in common])
        d_d_all = np.array([ft_pr[r]["ddc_ok"] - sp_pr[r]["ddc_ok"] for r in common
                            if sp_pr[r].get("ddc_ok") is not None
                            and ft_pr[r].get("ddc_ok") is not None])
        result["tests"][f"H2_{prov}"] = {
            "design": "strict paired (records where both metrics are defined)",
            "n_paired": n,
            "n_text_subset": len(common),
            "lcsh_any_level": {
                "sparse": round(float(np.mean([sp_pr[r]["any_level"] for r in strict])), 4),
                "fulltext": round(float(np.mean([ft_pr[r]["any_level"] for r in strict])), 4),
                "delta": round(float(dl.mean()), 4),
            },
            "ddc_class3": {
                "sparse": round(float(np.mean([sp_pr[r]["ddc_ok"] for r in strict])), 4),
                "fulltext": round(float(np.mean([ft_pr[r]["ddc_ok"] for r in strict])), 4),
                "delta": round(float(dd.mean()), 4),
            },
            "diff_of_diff": round(float(dl.mean() - dd.mean()), 4),
            "diff_of_diff_ci95": [round(float(lo), 4), round(float(hi), 4)],
            "supports_H2": bool(lo > 0),
            "note": "CI touching zero means the direction is supported but the "
                    "interaction is not resolved at this sample size; more "
                    "models/records (E3 multi-model) are needed",
            "loose_variant_unpaired": {
                "n_lcsh": len(d_l_all), "delta_lcsh": round(float(d_l_all.mean()), 4),
                "n_ddc": len(d_d_all), "delta_ddc": round(float(d_d_all.mean()), 4),
                "diff_of_diff": round(float(d_l_all.mean() - d_d_all.mean()), 4),
            },
        }

    # H3: representation gap present (DDC > LCSH) in every cell
    h3 = []
    for row in table:
        if row["gap"] is not None:
            h3.append({"cell": row["cell"], "gap": row["gap"], "holds": row["gap"] > 0})
    result["tests"]["H3"] = {"cells": h3,
                             "holds_in_all_cells": all(x["holds"] for x in h3) if h3 else None}
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=DEFAULT_MODELS,
                    help='comma list of provider:model, e.g. '
                         '"deepseek:deepseek-chat,gemini:gemini-2.5-pro"')
    ap.add_argument("--conditions", default=DEFAULT_CONDITIONS)
    ap.add_argument("--limit", type=int, default=0, help="0 = all records")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--text-cache", default=str(ROOT / "data" / "text_cache"))
    ap.add_argument("--cached-text-only", action="store_true",
                    help="pass through to eval_libra_cat: fulltext cells use "
                         "only records whose text excerpt is already cached")
    ap.add_argument("--no-authority", action="store_true",
                    help="skip id.loc.gov lookups when scoring (offline runs)")
    ap.add_argument("--score-only", action="store_true",
                    help="skip generation and score existing cell prediction "
                         "files (e.g. to reuse the shipped sparse run as the "
                         "anchor cell without re-calling the API)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan only")
    args = ap.parse_args()

    models = parse_models(args.models)
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    data_dir = ROOT / "data" / "e3"
    reports_dir = ROOT / "reports" / "e3"
    data_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    cells = [{"provider": m["provider"], "model": m["model"], "condition": c}
             for m in models for c in conditions]
    for c in cells:
        c["tag"] = cell_tag(c)
        c["preds"] = data_dir / f"preds_{c['tag']}.jsonl"
        c["scores"] = reports_dir / f"{c['tag']}_scores.json"
        c["per_record"] = reports_dir / f"{c['tag']}_per_record.json"

    print(f"E3: {len(cells)} cells "
          f"({len(models)} model(s) x {len(conditions)} condition(s))")
    if args.dry_run:
        print("(dry run — no API calls)\n")

    per_record: Dict[str, Dict] = {}
    for c in cells:
        print(f"\n=== cell {c['tag']}")
        if args.score_only:
            if not c["preds"].exists():
                print(f"  no predictions at {c['preds']}; skipping cell")
                continue
            print("  (score-only: reusing existing predictions)")
        else:
            gen = [sys.executable, str(SCRIPTS / "eval_libra_cat.py"),
                   "--provider", c["provider"], "--condition", c["condition"],
                   "--out", str(c["preds"]), "--workers", str(args.workers),
                   "--text-cache", args.text_cache]
            if c["model"]:
                gen += ["--model", c["model"]]
            if args.limit:
                gen += ["--limit", str(args.limit)]
            if args.resume:
                gen += ["--resume"]
            if args.cached_text_only:
                gen += ["--cached-text-only"]
            rc = run(gen, args.dry_run)
            if rc != 0:
                print(f"  generation failed (exit {rc}); skipping cell")
                continue
        score = [sys.executable, str(SCRIPTS / "score_libra_cat.py"),
                 "--preds", str(c["preds"]), "--out", str(c["scores"]),
                 "--per-record-out", str(c["per_record"])]
        if args.no_authority:
            score += ["--no-authority"]
        rc = run(score, args.dry_run)
        if rc != 0:
            print(f"  scoring failed (exit {rc}); skipping cell")
            continue
        if not args.dry_run and c["per_record"].exists():
            per_record[c["tag"]] = json.loads(c["per_record"].read_text())

    if args.dry_run:
        print("\ndry run complete; nothing written")
        return

    result = kappa_free_report(cells, per_record, reports_dir, args.dry_run)
    (ROOT / "reports" / "e3_scores.json").write_text(json.dumps(result, indent=1))

    lines = ["# E3 — multi-model acquisition comparison", "",
             "| cell | provider | model | condition | n | LCSH any-level | DDC class3 | gap |",
             "|---|---|---|---|---|---|---|---|"]
    for r in result["cells"]:
        lines.append(f"| {r['cell']} | {r['provider']} | {r['model']} | {r['condition']} "
                     f"| {r['n']} | {r['lcsh_any_level']} | {r['ddc_class3']} | {r['gap']} |")
    lines += ["", "## Hypothesis tests", ""]
    for k, v in result["tests"].items():
        lines.append(f"- **{k}**: {json.dumps(v)}")
    (ROOT / "reports" / "e3_scores.md").write_text("\n".join(lines) + "\n")
    print("\nwrote reports/e3_scores.json and reports/e3_scores.md")


if __name__ == "__main__":
    main()
