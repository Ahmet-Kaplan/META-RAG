#!/usr/bin/env python3
"""
evaluate.py — Evaluate retrieval + generation across META-RAG modes.

Metrics (retrieval): nDCG@10, P@5 over gold work_keys
Metrics (generation, meta/hybrid): citation-verification rate, judge-faithfulness

Usage:
  python3 evaluate.py --mode meta --questions 20
  python3 evaluate.py --all-modes --questions 20   # table over all modes
"""

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from retrieval import MetaIndex  # noqa: E402
from generate import generate, verify  # noqa: E402


# Chunk retrieval depth for the chunk->record mapping. 50 saturates: @50 and
# @200 give identical nDCG@10 for every mode on the scaled set.
CHUNK_DEPTH = 50


def ndcg_at_k(ranked_ids, gold_ids, k=10):
    gold = set(gold_ids)
    dcg = 0.0
    for i, rid in enumerate(ranked_ids[:k]):
        if rid in gold:
            dcg += 1.0 / math.log2(i + 2)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), k)))
    return dcg / idcg if idcg > 0 else 0.0


def precision_at_k(ranked_ids, gold_ids, k=5):
    gold = set(gold_ids)
    return sum(1 for rid in ranked_ids[:k] if rid in gold) / k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(ROOT / "data" / "index"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" / "libra_qa_drafts_polished.jsonl"))
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus.jsonl"))
    ap.add_argument("--mode", default="meta")
    ap.add_argument("--all-modes", action="store_true")
    ap.add_argument("--questions", type=int, default=20)
    ap.add_argument("--generate", action="store_true", help="run LLM generation + verification")
    ap.add_argument("--no-grounding", action="store_true",
                    help="generate WITHOUT the citation-grounding protocol (verification ablation)")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--report", default=str(ROOT / "reports" / "per_type_metrics.md"))
    args = ap.parse_args()

    with open(args.qa, encoding="utf-8") as f:
        qa = [json.loads(l) for l in f if l.strip()]
    with open(args.corpus, encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]
    corpus_keys = {r["work_key"] for r in corpus}
    by_key = {r["work_key"]: r for r in corpus}
    chunk_text_by_id = {}
    chunk_to_work = {}   # chunk_id -> work_key (for chunk->record mapping)
    for r in corpus:
        for c in r.get("chunks", []):
            if "text" in c:
                chunk_text_by_id[c["chunk_id"]] = c["text"]
            chunk_to_work[c["chunk_id"]] = r["work_key"]

    pool = [q for q in qa if q.get("work_key") in corpus_keys]
    import random
    rng = random.Random(args.seed)
    sample = rng.sample(pool, min(args.questions, len(pool)))
    print(f"Evaluation pool: {len(pool)} questions in-corpus; sampling {len(sample)}")
    # Silently evaluating on fewer questions than asked for is how a mismatched
    # --qa goes unnoticed: the run succeeds, the report looks normal, and n is
    # quietly a third of what the paper claims.
    if len(sample) < args.questions:
        raise SystemExit(
            f"asked for {args.questions} questions but only {len(pool)} of "
            f"{len(qa)} in {args.qa} fall inside {args.corpus}. Pass the question "
            f"file that matches this corpus, or lower --questions deliberately.")

    idx = MetaIndex(args.index)
    # A corpus that does not cover the index is the silent killer here: the
    # ranking still works (it reads the index), but by_key lookups miss, so the
    # generator is handed an empty evidence set and dutifully answers "the
    # provided sources contain no catalog records". --corpus defaults to the
    # 30-record pilot, so this is one forgotten flag away at all times.
    _covered = len(corpus_keys & set(idx.record_ids))
    if _covered < 0.9 * len(idx.record_ids):
        raise SystemExit(
            f"--corpus covers only {_covered} of {len(idx.record_ids)} records in "
            f"{args.index}. Retrieval would score against the index while generation "
            f"and the question pool used the corpus; pass the corpus this index was "
            f"built from.")
    modes = ["dense", "bm25", "hybrid", "meta"] if args.all_modes else [args.mode]

    # per-question results: results[mode] = [ {type, ndcg, p5} ... ]
    results = {m: [] for m in modes}
    results_mode_gen = {}
    for mode in modes:
        gen_stats = {"n": 0, "has_citation": 0, "all_verified": 0,
                     "judge_true": 0, "judge_false": 0, "judge_error": 0}
        for q in sample:
            gold = [q["work_key"]]
            # Retrieval depth must be deep enough that the chunk->record mapping
            # below can yield 10 distinct records; nDCG@10 against a 5-chunk list
            # capped the metadata-blind baselines at ~3 candidates. Generation
            # context is unaffected (it uses chunks[:4], the same top-4).
            # In meta mode the record ranking never depends on the chunk
            # rankings, so when we are not generating, skip chunk retrieval
            # entirely -- BM25 over ~460k chunks dominates otherwise. Verified
            # to produce identical record rankings.
            chunks, records = idx.retrieve(
                q["question_polished"], mode=mode, topk_chunks=CHUNK_DEPTH,
                skip_chunks=(mode == "meta" and not args.generate))
            if mode in ("meta", "meta4"):
                rec_ids = [r for r, s in records]
            else:
                # metadata-blind baselines rank chunks; map chunks -> records
                rec_ids, seen = [], set()
                for cid, _s in chunks:
                    wk = chunk_to_work.get(cid)
                    if wk and wk not in seen:
                        seen.add(wk)
                        rec_ids.append(wk)
                rec_ids = rec_ids[:10]
            results[mode].append({"type": q["type"], "ndcg": ndcg_at_k(rec_ids, gold),
                                  "p5": precision_at_k(rec_ids, gold)})
            if args.generate and mode in ("meta", "hybrid"):
                gen_stats["n"] += 1
                rec_objs = [by_key[r] for r, s in records[:5] if r in by_key]
                chunk_objs = [{"chunk_id": cid, "text": chunk_text_by_id[cid]} for cid, s in chunks[:4] if cid in chunk_text_by_id]
                answer = generate(q["question_polished"], rec_objs, chunk_objs, grounding=not args.no_grounding)
                v = verify(answer, rec_objs, chunk_objs, question=q["question_polished"])
                gen_stats["has_citation"] += int(v["has_citations"])
                gen_stats["all_verified"] += int(v["all_citations_verified"])
                # judge_faithful is None when the judge call itself failed.
                # Counting None as "unfaithful" silently deflates the rate, so
                # failures are tracked separately and excluded from the rate.
                if v["judge_faithful"] is None:
                    gen_stats["judge_error"] += 1
                elif v["judge_faithful"]:
                    gen_stats["judge_true"] += 1
                else:
                    gen_stats["judge_false"] += 1
                gen_stats["examples"] = gen_stats.get("examples", [])
                if len(gen_stats["examples"]) < 5:
                    gen_stats["examples"].append({
                        "type": q["type"], "question": q["question_polished"],
                        "answer": answer[:400],
                        "cited_recs": v["cited_recs"][:5], "cited_chunks": v["cited_chunks"][:5],
                        "all_citations_verified": v["all_citations_verified"],
                        "judge_faithful": v["judge_faithful"],
                    })
        results_mode_gen[mode] = gen_stats
        if gen_stats["n"]:
            print(f"[gen {mode}] citations: {gen_stats['has_citation']}/{gen_stats['n']}"
                  f"  verified: {gen_stats['all_verified']}/{gen_stats['n']}"
                  f"  judge-faithful: {gen_stats['judge_true']}"
                  f"/{gen_stats['judge_true'] + gen_stats['judge_false']}"
                  f"  judge-errors: {gen_stats['judge_error']}")

    # ---- overall ----
    for mode in modes:
        n = len(results[mode])
        ndcg = sum(r["ndcg"] for r in results[mode]) / max(1, n)
        p5 = sum(r["p5"] for r in results[mode]) / max(1, n)
        print(f"[{mode}] nDCG@10={ndcg:.3f}  P@5={p5:.3f}  (n={n})")

    # ---- per-type ----
    types = ["known_item", "topical", "bib_fact"]
    print("\nPer-type nDCG@10:")
    header = f"{'type':<12}" + "".join(f"{m:>9}" for m in modes)
    print(header)
    per_type = {}
    for t in types:
        row = []
        for m in modes:
            vals = [r["ndcg"] for r in results[m] if r["type"] == t]
            row.append(sum(vals) / max(1, len(vals)) if vals else float("nan"))
        per_type[t] = {m: row[i] for i, m in enumerate(modes)}
        print(f"{t:<12}" + "".join(f"{v:>9.3f}" for v in row))

    # ---- paired permutation test: meta vs best metadata-blind baseline ----
    def perm_pvalue(a, b, iters=2000, seed=args.seed):
        import random as _r
        rng = _r.Random(seed)
        diffs = [x - y for x, y in zip(a, b)]
        obs = abs(sum(diffs))
        cnt = 0
        for _ in range(iters):
            s = sum(d if rng.random() < 0.5 else -d for d in diffs)
            if abs(s) >= obs:
                cnt += 1
        return (cnt + 1) / (iters + 1)

    print("\nPaired permutation test (meta vs hybrid), nDCG@10:")
    perm_lines = []
    if "meta" in results and "hybrid" in results:
        for t in types:
            a = [r["ndcg"] for r in results["meta"] if r["type"] == t]
            b = [r["ndcg"] for r in results["hybrid"] if r["type"] == t]
            if len(a) >= 5 and len(a) == len(b):
                p = perm_pvalue(a, b)
                line = f"  {t:<12} meta={per_type[t]['meta']:.3f} hybrid={per_type[t]['hybrid']:.3f}  p={p:.3f}"
                print(line)
                perm_lines.append((t, p))
    else:
        print("  (skipped: hybrid not evaluated in this run)")

    # ---- report ----
    md = ["# Per-type metric breakdown (META-RAG pilot)",
          "",
          f"- Corpus: {len(corpus)} books · Questions: {len(sample)} · Pool in corpus: {len(pool)}",
          "",
          "| type | " + " | ".join(modes) + " |",
          "|---|" + "---|" * len(modes)]
    for t in types:
        md.append(f"| {t} | " + " | ".join(f"{per_type[t][m]:.3f}" for m in modes) + " |")
    md += ["", "**Paired permutation test (meta vs hybrid, nDCG@10):**", ""]
    for t, p in perm_lines:
        md.append(f"- {t}: p={p:.3f}")
    out = Path(args.report)
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nReport -> {out}")

    # structured JSON alongside the markdown report (for paper auto-update)
    json_out = out.with_suffix(".json")
    gen_report = {}
    for mode in ("meta", "hybrid"):
        gs = results_mode_gen.get(mode)
        if gs and gs.get("n"):
            gen_report[mode] = {
                "n": gs["n"],
                "with_citations": gs["has_citation"],
                "citations_verified": gs["all_verified"],
                "judge_faithful": gs["judge_true"],
                "judge_unfaithful": gs["judge_false"],
                "judge_errors": gs["judge_error"],
                "n_judged": gs["judge_true"] + gs["judge_false"],
                "rate_citations": round(gs["has_citation"] / gs["n"], 3),
                "rate_verified": round(gs["all_verified"] / gs["n"], 3),
                # over successfully judged answers, not over n
                "rate_faithful": (round(gs["judge_true"] /
                                        (gs["judge_true"] + gs["judge_false"]), 3)
                                  if (gs["judge_true"] + gs["judge_false"]) else None),
                "examples": gs.get("examples", []),
            }
    json_out.write_text(json.dumps({
        "n_questions": len(sample),
        "n_books": len(corpus),
        "n_chunks": sum(r.get("n_chunks", 0) for r in corpus),
        "per_type": {t: {m: per_type[t][m] for m in modes} for t in types},
        "overall": {m: round(sum(r["ndcg"] for r in results[m]) / max(1, len(results[m])), 3) for m in modes},
        "permutation": {t: p for t, p in perm_lines},
        "generation": gen_report,
    }, indent=2), encoding="utf-8")
    print(f"JSON -> {json_out}")

    report = {
        "mode": args.mode, "questions": len(sample),
        "pool_in_corpus": len(pool), "total_qa": len(qa),
    }
    (ROOT / "reports" / "eval_summary.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
