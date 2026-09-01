#!/usr/bin/env python3
"""
compare_hathi_gold.py — Compare HathiTrust professional MARC against our gold.

Subjects:  HathiTrust LCSH (650)  vs  Gutenberg LCSH gold
DDC:       HathiTrust 082/092      vs  OpenLibrary ddc gold

Outputs reports/hathi_enrichment_report.md

Usage:
  python3 compare_hathi_gold.py [--enrichment ../data/hathi_enrichment.jsonl]
"""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(h):
    return re.sub(r"[^a-z0-9]", " ", h.lower())


def overlap_report(gold_list, ht_list, label):
    if not gold_list or not ht_list:
        return None
    g = set(norm(h) for h in gold_list)
    h = set(norm(h) for h in ht_list)
    recall = len(g & h) / len(g)      # fraction of gold headings found in HT
    precision = len(g & h) / len(h)   # fraction of HT headings that are in gold
    exact_any = any(norm(a) == norm(b) for a in gold_list for b in ht_list)
    return {"label": label, "recall": recall, "precision": precision,
            "n_gold": len(g), "n_ht": len(h), "exact_any": exact_any}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enrichment", default=str(ROOT / "data" / "hathi_enrichment.jsonl"))
    ap.add_argument("--matches", default=str(ROOT / "data" / "join_pilot_matches.jsonl"))
    ap.add_argument("--report", default=str(ROOT / "reports" / "hathi_enrichment_report.md"))
    args = ap.parse_args()

    with open(args.enrichment, encoding="utf-8") as f:
        enr = [json.loads(l) for l in f if l.strip()]
    by_key = {r["work_key"]: r for r in enr}
    with open(args.matches, encoding="utf-8") as f:
        matches = [json.loads(l) for l in f if l.strip()]

    subj_rows, ddc_rows = [], []
    agree_subj = agree_ddc = both = 0
    for m in matches:
        e = by_key.get(m["work_key"])
        if not e:
            continue
        gut_lcsh = [s for s in (m.get("gutenberg_subjects") or []) if " -- " in s]
        ol_ddc = [d for d in (m.get("ddc") or []) if re.match(r"^\d{3}(\.\d+)?$", d)]
        ht_subj = e.get("ht_subjects") or []
        ht_ddc = e.get("ht_ddc") or []
        if gut_lcsh and ht_subj:
            subj_rows.append(overlap_report(gut_lcsh, ht_subj, "gutenberg-vs-HT"))
            if subj_rows[-1]["exact_any"]:
                agree_subj += 1
        if ol_ddc and ht_ddc:
            ddc_rows.append(overlap_report(ol_ddc, ht_ddc, "OL-vs-HT"))
            if ddc_rows[-1]["exact_any"]:
                agree_ddc += 1
        if (gut_lcsh and ht_subj) and (ol_ddc and ht_ddc):
            both += 1

    n_subj = len(subj_rows)
    n_ddc = len(ddc_rows)
    r = f"""# HathiTrust Enrichment Report (professional MARC vs. our gold)

- Books enriched: {len(enr)}
- Books with both gold subjects and HT subjects: {n_subj}
- Books with both OL DDC and HT DDC: {n_ddc}
- Books with all four signals: {both}

## Subjects (Gutenberg LCSH vs HathiTrust LCSH)

- Books where >=1 gold heading matches a HT heading: **{agree_subj}/{n_subj}** ({100*agree_subj/max(1,n_subj):.0f}%)
- Mean heading recall (fraction of gold headings found in HT): **{100*sum(r['recall'] for r in subj_rows)/max(1,n_subj):.0f}%**
- Mean heading precision (fraction of HT headings present in gold): **{100*sum(r['precision'] for r in subj_rows)/max(1,n_subj):.0f}%**

## DDC (OpenLibrary vs HathiTrust 082)

- Books where >=1 OL ddc matches a HT ddc exactly: **{agree_ddc}/{n_ddc}** ({100*agree_ddc/max(1,n_ddc):.0f}%)
- Books where 3-digit class matches (any): """
    class_match = sum(1 for m in matches if (e := by_key.get(m["work_key"])) and
                      any((d1 or "")[:3] == (d2 or "")[:3]
                          for d1 in (m.get("ddc") or []) for d2 in (e.get("ht_ddc") or [])))
    r += f"**{class_match}/{n_ddc}** ({100*class_match/max(1,n_ddc):.0f}%)\n\n"

    r += "## Example records (agreement / disagreement)\n\n| Book | Gold LCSH | HT LCSH | Gold DDC | HT DDC |\n|---|---|---|---|---|\n"
    shown = 0
    for m in matches:
        e = by_key.get(m["work_key"])
        if not e:
            continue
        gut = [s for s in (m.get("gutenberg_subjects") or []) if " -- " in s][:2]
        ol = [d for d in (m.get("ddc") or []) if re.match(r"^\d{3}(\.\d+)?$", d)][:2]
        ht_s, ht_d = (e.get("ht_subjects") or [])[:2], (e.get("ht_ddc") or [])[:2]
        if gut or ht_s:
            r += (f"| {str(m.get('gutenberg_title'))[:38]} | {', '.join(gut)[:60] or '-'} | "
                  f"{', '.join(ht_s)[:60] or '-'} | {', '.join(ol) or '-'} | {', '.join(ht_d) or '-'} |\n")
            shown += 1
        if shown >= 10:
            break

    with open(args.report, "w", encoding="utf-8") as f:
        f.write(r)
    print(r[:1200])
    print(f"\nReport -> {args.report}")


if __name__ == "__main__":
    main()
