#!/usr/bin/env python3
"""
pooled_eval.py — Replace single-gold topical scoring with pooled graded relevance.

LIBRA-QA scores a topical question against the one record it was generated
from. On a 227-book collection a query like "a novel about impostors" has many
correct answers, so single-gold nDCG penalises a system for returning a
genuinely relevant book that happens not to be the seed record. Every topical
number in the paper inherits that error.

This applies the standard TREC remedy. For each topical question, the top-10
records from every configuration under comparison are pooled; a judge then
grades each pooled candidate against the query (0 not relevant, 1 marginal,
2 relevant) without being told which record seeded the question. All
configurations are then rescored with graded nDCG@10 over those judgments.

What this fixes: the measurement. Systems are credited for any relevant record.
What it does not fix: the queries are still paraphrases of a record's own
subject heading, so the query distribution remains unrepresentative of real
patron search. See Limitations.

Stages (run in order; each caches to phase2/reports/):
  runs    retrieve top-10 records per config per topical question
  judge   pool and grade with the LLM judge
  score   graded nDCG@10 per config, against single-gold

Usage:
  python3 phase2/scripts/pooled_eval.py
"""

import argparse
import json
import logging
import math
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "scripts"))
from retrieval import MetaIndex  # noqa: E402
from llm_client import chat_json  # noqa: E402

logger = logging.getLogger(__name__)

# (name, index dir, retrieval mode) -- the systems whose rankings are pooled.
def build_configs(prefix: str):
    """Index dirs are derived from --index-prefix. They were hardcoded to
    index_scaled, so after the record index was rebuilt without DDC this check
    went on scoring the old one while the rest of the paper moved."""
    return [
        ("dense", prefix, "dense"),
        ("bm25", prefix, "bm25"),
        ("hybrid", prefix, "hybrid"),
        ("meta", prefix, "meta"),
        ("loop_none", f"{prefix}_loop_none", "meta"),
        ("loop_llm", f"{prefix}_loop_llm", "meta"),
        ("loop_gold", f"{prefix}_loop_gold", "meta"),
        ("sparsity_base100", f"{prefix}_sp_base1.00", "meta"),
        ("sparsity_enr100", f"{prefix}_sp_enr1.00", "meta"),
    ]

JUDGE_SYSTEM = (
    "You are a reference librarian judging whether books are relevant to a "
    "patron's topical request. Judge the book, not the wording. Be strict: a "
    "book is relevant only if a patron making this request would be glad to "
    "receive it."
)

JUDGE_PROMPT = """Patron request: {query}

Candidate books from the collection:
{candidates}

For each candidate, grade relevance to the request:
  2 = clearly relevant, a good answer to the request
  1 = marginally relevant, related but a poor answer
  0 = not relevant

Respond ONLY with JSON mapping each candidate number to its grade:
{{"1": 2, "2": 0, ...}}"""


def dcg(grades: List[float]) -> float:
    return sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(grades))


def graded_ndcg(ranked: List[str], qrel: Dict[str, int], k: int = 10) -> float:
    got = [qrel.get(r, 0) for r in ranked[:k]]
    ideal = sorted(qrel.values(), reverse=True)[:k]
    denom = dcg([float(g) for g in ideal])
    return dcg([float(g) for g in got]) / denom if denom > 0 else 0.0


def single_gold_ndcg(ranked: List[str], gold: str, k: int = 10) -> float:
    return sum(1 / math.log2(i + 2) for i, r in enumerate(ranked[:k]) if r == gold)


# --------------------------------------------------------------------------

def stage_runs(questions: List[Dict], corpus_keys: set, args) -> Dict:
    runs: Dict[str, Dict[str, List[str]]] = {}
    for name, idx_name, mode in build_configs(args.index_prefix):
        idx_dir = ROOT / "data" / idx_name
        if not idx_dir.exists():
            logger.warning("skipping %s: %s not found", name, idx_dir)
            continue
        idx = MetaIndex(str(idx_dir))
        per_q = {}
        for q in questions:
            chunks, records = idx.retrieve(q["question_polished"], mode=mode,
                                           topk_chunks=50)
            if mode == "meta":
                rec_ids = [r for r, _ in records]
            else:
                rec_ids, seen = [], set()
                for cid, _ in chunks:
                    wk = args.chunk_to_work.get(cid)
                    if wk and wk not in seen:
                        seen.add(wk)
                        rec_ids.append(wk)
                rec_ids = rec_ids[:10]
            per_q[q["qid"]] = rec_ids[:10]
        runs[name] = per_q
        logger.info("ran %s (%d queries)", name, len(per_q))
    return runs


def stage_judge(questions: List[Dict], runs: Dict, by_key: Dict, workers: int,
                prior: Optional[Dict] = None) -> Dict:
    pools = {}
    for q in questions:
        pool = []
        for per_q in runs.values():
            for r in per_q.get(q["qid"], []):
                if r not in pool:
                    pool.append(r)
        pools[q["qid"]] = pool
    sizes = [len(p) for p in pools.values()]
    logger.info("pool: mean %.1f candidates/query (min %d, max %d)",
                sum(sizes) / len(sizes), min(sizes), max(sizes))

    prior = prior or {}
    qrels: Dict[str, Dict[str, int]] = {k: dict(v) for k, v in prior.items()}
    lock = threading.Lock()
    failures = [0]
    todo = [q for q in questions
            if any(wk not in prior.get(q["qid"], {}) for wk in pools[q["qid"]])]
    logger.info("%d/%d queries need judging (%d already fully graded)",
                len(todo), len(questions), len(questions) - len(todo))

    def judge(q: Dict) -> None:
        graded_before = prior.get(q["qid"], {})
        pool = [wk for wk in pools[q["qid"]] if wk not in graded_before]
        lines = []
        for i, wk in enumerate(pool, 1):
            rec = by_key.get(wk, {})
            subj = "; ".join((rec.get("subjects") or [])[:4]) or "(no subject headings)"
            authors = "; ".join(rec.get("authors") or [])
            lines.append(f'{i}. "{rec.get("title", "?")}" by {authors or "?"} — subjects: {subj}')
        try:
            resp = chat_json(
                JUDGE_PROMPT.format(query=q["question_polished"], candidates="\n".join(lines)),
                system=JUDGE_SYSTEM, temperature=0.0, max_tokens=1200)
        except Exception as exc:
            with lock:
                failures[0] += 1
            logger.warning("judge failed for %s: %s", q["qid"], exc)
            return
        graded = {}
        for k, v in (resp or {}).items():
            try:
                i = int(str(k).strip())
                g = int(v)
            except (ValueError, TypeError):
                continue
            if 1 <= i <= len(pool) and g in (0, 1, 2):
                graded[pool[i - 1]] = g
        with lock:
            qrels.setdefault(q["qid"], {}).update(graded)

    with ThreadPoolExecutor(max_workers=workers) as pool_exec:
        list(pool_exec.map(judge, todo))
    logger.info("judged %d queries (%d judge failures); %d queries have grades",
                len(todo), failures[0], len(qrels))
    return qrels


def stage_score(questions: List[Dict], runs: Dict, qrels: Dict) -> Dict:
    usable = [q for q in questions if qrels.get(q["qid"])]
    logger.info("scoring %d queries with judgments", len(usable))
    out = {}
    for name, per_q in runs.items():
        g = [graded_ndcg(per_q[q["qid"]], qrels[q["qid"]]) for q in usable]
        s = [single_gold_ndcg(per_q[q["qid"]], q["work_key"]) for q in usable]
        out[name] = {"graded_ndcg10": round(sum(g) / len(g), 3),
                     "single_gold_ndcg10": round(sum(s) / len(s), 3)}
    rel = [sum(1 for v in qrels[q["qid"]].values() if v == 2) for q in usable]
    out["_meta"] = {
        "n_queries": len(usable),
        "mean_relevant_per_query": round(sum(rel) / len(rel), 2),
        "queries_with_multiple_relevant": sum(1 for r in rel if r > 1),
    }
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--refresh-runs", action="store_true",
                    help="re-run retrieval even if the cache matches the prefix")
    ap.add_argument("--index-prefix", default="index_scaled_ts")
    ap.add_argument("--questions", type=int, default=300)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    corpus = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    by_key = {r["work_key"]: r for r in corpus}
    corpus_keys = set(by_key)
    args.chunk_to_work = {c["chunk_id"]: r["work_key"] for r in corpus
                          for c in r.get("chunks", []) if c.get("chunk_id")}

    qa = [json.loads(l) for l in open(args.qa, encoding="utf-8") if l.strip()]
    pool_q = [q for q in qa if q.get("work_key") in corpus_keys]
    sample = random.Random(args.seed).sample(pool_q, min(args.questions, len(pool_q)))
    topical = [q for q in sample if q["type"] == "topical"]
    logger.info("%d topical questions in the evaluation sample", len(topical))

    runs_path = ROOT / "reports" / "pooled_runs.json"
    # The cache is keyed by the index prefix it was produced from. Without this
    # the cache silently outlived a rebuild of the record index: --index-prefix
    # was honoured by stage_runs and then never reached, so the pooled check
    # kept validating the superseded system.
    cached = json.loads(runs_path.read_text()) if runs_path.exists() else {}
    if cached.get("_index_prefix") == args.index_prefix and not args.refresh_runs:
        runs = {k: v for k, v in cached.items() if not k.startswith("_")}
        logger.info("loaded cached runs (%d configs, prefix=%s)", len(runs), args.index_prefix)
    else:
        if cached:
            logger.info("runs cache was built from prefix=%s, need %s: re-running",
                        cached.get("_index_prefix", "<unrecorded>"), args.index_prefix)
        runs = stage_runs(topical, corpus_keys, args)
        runs_path.write_text(json.dumps({**runs, "_index_prefix": args.index_prefix}))

    qrels_path = ROOT / "reports" / "pooled_qrels.json"
    prior = json.loads(qrels_path.read_text()) if qrels_path.exists() else {}
    if prior:
        logger.info("loaded %d cached queries of judgments", len(prior))
    # A grade is a property of (query, record), not of the run that surfaced it,
    # and the judge is never told which system proposed a candidate -- so grades
    # carry over and only newly-pooled candidates cost an LLM call.
    qrels = stage_judge(topical, runs, by_key, args.workers, prior=prior)
    qrels_path.write_text(json.dumps(qrels))

    scores = stage_score(topical, runs, qrels)
    (ROOT / "reports" / "pooled_eval.json").write_text(json.dumps(scores, indent=2))

    # Paper macros. pooled_numbers.tex claimed to be auto-generated but nothing
    # produced it, so it was hand-maintained and silently outlived two index
    # rebuilds. Both columns are emitted from THIS run so the paper's table
    # compares single-gold against graded on the same questions -- mixing in the
    # full-pool retrieval macros would compare different question sets.
    TEXNAME = {"dense": "Dense", "bm25": "Bm", "hybrid": "Hybrid", "meta": "Meta",
               "loop_none": "LoopNone", "loop_llm": "LoopLlm", "loop_gold": "LoopGold",
               "sparsity_base100": "SpBase", "sparsity_enr100": "SpEnr"}
    tex = ["% pooled_numbers.tex - AUTO-GENERATED by pooled_eval.py "
           f"(index_prefix={args.index_prefix}, n={scores['_meta']['n_queries']})."]
    for k, name in TEXNAME.items():
        if k not in scores:
            continue
        tex.append(r"\newcommand{\Pool" + name + r"}{" +
                   f"{scores[k]['graded_ndcg10']:.3f}" + "}")
        tex.append(r"\newcommand{\PoolSingle" + name + r"}{" +
                   f"{scores[k]['single_gold_ndcg10']:.3f}" + "}")
    _m = scores["_meta"]
    tex.append(r"\newcommand{\PoolNQueries}{" + str(_m["n_queries"]) + "}")
    tex.append(r"\newcommand{\PoolMeanRel}{" + str(_m["mean_relevant_per_query"]) + "}")
    tex.append(r"\newcommand{\PoolMultiRel}{" + str(_m["queries_with_multiple_relevant"]) + "}")
    if "sparsity_enr100" in scores and "sparsity_base100" in scores:
        tex.append(r"\newcommand{\PoolEnrGain}{" +
                   f"{scores['sparsity_enr100']['graded_ndcg10'] - scores['sparsity_base100']['graded_ndcg10']:.3f}" + "}")
        tex.append(r"\newcommand{\PoolSingleEnrGain}{" +
                   f"{scores['sparsity_enr100']['single_gold_ndcg10'] - scores['sparsity_base100']['single_gold_ndcg10']:.3f}" + "}")
    (ROOT.parent / "paper" / "pooled_numbers.tex").write_text("\n".join(tex) + "\n")
    logger.info("wrote paper/pooled_numbers.tex")

    m = scores.pop("_meta")
    md = ["# Pooled graded relevance for topical questions", "",
          f"- {m['n_queries']} topical questions, pooled top-10 from {len(runs)} configurations",
          f"- Mean fully-relevant records per query: **{m['mean_relevant_per_query']}**",
          f"- Queries with more than one fully-relevant record: "
          f"**{m['queries_with_multiple_relevant']}/{m['n_queries']}**", "",
          "| Configuration | single-gold nDCG@10 | graded nDCG@10 | delta |",
          "|---|---|---|---|"]
    for name, v in scores.items():
        md.append(f"| {name} | {v['single_gold_ndcg10']:.3f} | **{v['graded_ndcg10']:.3f}** | "
                  f"{v['graded_ndcg10'] - v['single_gold_ndcg10']:+.3f} |")
    md += ["", "Judgments are LLM-derived and not yet human-validated; a human-judged",
           "subsample is required before these are treated as gold."]
    (ROOT / "reports" / "pooled_eval.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
