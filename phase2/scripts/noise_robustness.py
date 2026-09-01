#!/usr/bin/env python3
"""
noise_robustness.py — Metadata corruption sweep (robustness ablation).

Hypothesis under test: discovery quality degrades monotonically with metadata
quality. Corrupt a fraction p of records' subjects/DDC with plausible-wrong
values (sampled from the corpus, mirroring the error taxonomy) or by dropping
them (under-cataloging), rebuild the record side of the index, and evaluate
META-RAG on the same questions.

Outputs:
  phase2/data/corpus_scaled_records_noise{p}.jsonl  (records only, no chunks)
  phase2/data/index_scaled_n{p}/                     (record index variants)
  phase2/reports/robustness.json + robustness.md
  figures/fig_robustness.pdf/.png                   (degradation curve)

Usage:
  HF_HOME="$PWD/.hf_cache" python3 phase2/scripts/noise_robustness.py
"""

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

CORRUPT_SUBJECTS_KEEP = 0.7   # fraction of corruptions that swap vs drop (subjects)
CORRUPT_DDC_KEEP = 0.7


def corrupt(rec, rate, rng, subj_pool, ddc_pool):
    """With prob ~rate per field, corrupt subjects/DDC with plausible-wrong
    values or drop them entirely. Returns a shallow copy (chunks untouched)."""
    r = dict(rec)
    if rng.random() < rate:
        subs = r.get("subjects") or []
        if subs and rng.random() < CORRUPT_SUBJECTS_KEEP:
            n = len(subs)
            r["subjects"] = [rng.choice(subj_pool) for _ in range(max(1, n))][:n]
        else:
            r["subjects"] = []
    if rng.random() < rate:
        ddc = r.get("ddc") or []
        if ddc and rng.random() < CORRUPT_DDC_KEEP:
            r["ddc"] = [rng.choice(ddc_pool)]
        else:
            r["ddc"] = []
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--chunk-index", default=str(ROOT / "data" / "index_scaled"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" / "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--rates", default="0,0.25,0.5,0.75,1.0")
    ap.add_argument("--questions", type=int, default=300)
    ap.add_argument("--fields", default="title+subj",
                    help="record index fields; DDC is excluded by default "
                         "(see reports/field_ablation.md)")
    ap.add_argument("--index-prefix", default="index_scaled_ts")
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    with open(args.corpus, encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]
    subj_pool = [s for r in corpus for s in (r.get("subjects") or [])]
    ddc_pool = [d for r in corpus for d in (r.get("ddc") or [])]
    print(f"corpus: {len(corpus)} records; subject pool: {len(subj_pool)}; ddc pool: {len(ddc_pool)}")

    rates = [float(x) for x in args.rates.split(",")]
    results = {"rates": rates, "overall": {}, "per_type": {}}
    for rate in rates:
        rng = random.Random(args.seed)
        recs = [corrupt(r, rate, rng, subj_pool, ddc_pool) for r in corpus]
        for r in recs:
            r.pop("chunks", None)  # records-only file
        rec_path = ROOT / "data" / f"corpus_scaled_records_noise{rate:.2f}.jsonl"
        rec_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")

        idx_dir = ROOT / "data" / f"{args.index_prefix}_n{rate:.2f}"
        r1 = subprocess.run([PY, "scripts/index.py", "--corpus", str(rec_path),
                             "--outdir", str(idx_dir), "--fields", args.fields,
                             "--records-only", "--chunk-index", args.chunk_index],
                            cwd=ROOT, capture_output=True, text=True)
        if r1.returncode != 0:
            print(f"[rate={rate}] index FAILED: {r1.stderr[-400:]}")
            continue
        rep = ROOT / "reports" / f"noise_{rate:.2f}.md"
        r2 = subprocess.run([PY, "scripts/evaluate.py", "--index", str(idx_dir),
                             "--qa", args.qa, "--corpus", str(rec_path),
                             "--mode", "meta", "--questions", str(args.questions),
                             "--report", str(rep)],
                            cwd=ROOT, capture_output=True, text=True)
        jp = rep.with_suffix(".json")
        if r2.returncode == 0 and jp.exists():
            j = json.loads(jp.read_text())
            results["overall"][rate] = j["overall"]["meta"]
            results["per_type"][rate] = {t: j["per_type"][t]["meta"] for t in
                                         ("known_item", "topical", "bib_fact")}
            print(f"[rate={rate:.2f}] overall={results['overall'][rate]:.3f} "
                  f"topical={results['per_type'][rate]['topical']:.3f}")
        else:
            print(f"[rate={rate:.2f}] eval FAILED: {r2.stderr[-400:]}")

    (ROOT / "reports" / "robustness.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    md = ["# Robustness: metadata corruption sweep", "",
          f"- {len(corpus)} books, {args.questions} questions, META-RAG (full fields)",
          "", "| corruption rate | overall | known_item | topical | bib_fact |",
          "|---|---|---|---|---|"]
    for rate in rates:
        if rate in results["overall"]:
            pt = results["per_type"][rate]
            md.append(f"| {rate:.0%} | {results['overall'][rate]:.3f} | {pt['known_item']:.3f} | "
                      f"{pt['topical']:.3f} | {pt['bib_fact']:.3f} |")
    (ROOT / "reports" / "robustness.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\nReport -> reports/robustness.md (+ .json)")


if __name__ == "__main__":
    main()
