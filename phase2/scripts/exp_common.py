#!/usr/bin/env python3
"""
exp_common.py — Shared plumbing for the extended-paper experiments
(field_ablation.py, selective_enrichment.py, gain_law.py).

Every one of them does the same three things: write a records-only corpus,
build a record index over it, and score the full question pool in meta mode.
The chunk side is never touched (meta-mode record rankings do not depend on
chunk rankings, see MetaIndex.retrieve), so a stub chunk index is enough for
collections that have no chunk index built.
"""

import json
import logging
import math
import pickle
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TYPES = ("known_item", "topical", "bib_fact")

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- IO

def read_jsonl(path) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(rows: Iterable[Dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def slim_corpus(src: Path, dest: Path) -> List[Dict]:
    """Records without chunks, cached. corpus_1300.jsonl is 769 MB with chunks;
    re-parsing it once per index build is the whole runtime otherwise."""
    if dest.exists():
        return read_jsonl(dest)
    # streamed: corpus_1300.jsonl holds every chunk's text, and materializing
    # the parsed records before dropping the chunks costs several GB
    dest.parent.mkdir(parents=True, exist_ok=True)
    recs = []
    with open(src, encoding="utf-8") as fin, open(dest, "w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            r = {k: v for k, v in json.loads(line).items() if k != "chunks"}
            recs.append(r)
            fout.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.info("slimmed %s -> %s (%d records)", src.name, dest.name, len(recs))
    return recs


def load_predictions(paths: Sequence[Path]) -> Dict[str, Dict]:
    """work_key -> LLM cataloging prediction, skipping failed generations."""
    preds: Dict[str, Dict] = {}
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        for r in read_jsonl(p):
            if not r.get("error"):
                preds[r["work_key"]] = r
    return preds


def enrich(rec: Dict, preds: Dict[str, Dict]) -> Dict:
    """Write LLM headings into a record that has none. Returns a new record;
    the input is never mutated (indexes are built from several variants of the
    same corpus in one process)."""
    r = dict(rec)
    if r.get("subjects"):
        return r
    p = preds.get(r["work_key"])
    if not p:
        return r
    r["subjects"] = list(p.get("pred_subjects") or [])
    r["ddc"] = [p["pred_ddc"]] if p.get("pred_ddc") else []
    return r


def strip_meta(rec: Dict) -> Dict:
    r = dict(rec)
    r["subjects"], r["ddc"] = [], []
    return r


# ------------------------------------------------------------------- indexing

def stub_chunk_index(path: Path) -> Path:
    """A chunk index with no chunks, for collections whose chunk side was never
    built. Legal only for meta-mode record scoring (skip_chunks=True)."""
    path.mkdir(parents=True, exist_ok=True)
    if not (path / "chunk_ids.json").exists():
        (path / "chunk_ids.json").write_text("[]")
        (path / "chunk_to_work.json").write_text("{}")
        (path / "chunk_tokens.pkl").write_bytes(pickle.dumps([]))
    return path


def build_index(records: List[Dict], tag: str, chunk_index: Path,
                fields: str = "title+subj+ddc", force: bool = False) -> Path:
    """Records-only index at data/index_<tag>. Skipped when it already exists."""
    idx_dir = ROOT / "data" / f"index_{tag}"
    if idx_dir.exists() and (idx_dir / "record_emb.npy").exists() and not force:
        logger.info("reuse %s", idx_dir.name)
        return idx_dir
    rec_path = write_jsonl(records, ROOT / "data" / f"records_{tag}.jsonl")
    r = subprocess.run(
        [PY, "scripts/index.py", "--corpus", str(rec_path), "--outdir", str(idx_dir),
         "--fields", fields, "--records-only", "--chunk-index", str(chunk_index)],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"[{tag}] index failed:\n{r.stdout[-800:]}\n{r.stderr[-800:]}")
    return idx_dir


# -------------------------------------------------------------------- scoring

def ndcg_at_10(ranked: Sequence[str], gold: str) -> float:
    return sum(1 / math.log2(i + 2) for i, r in enumerate(ranked[:10]) if r == gold)


_QVEC: Dict[int, object] = {}


def query_vectors(pool: List[Dict]):
    """Embed the question pool once. Every sweep scores the same questions
    against dozens of record indexes, and re-embedding them per index was the
    dominant cost."""
    key = id(pool)
    if key not in _QVEC:
        sys.path.insert(0, str(ROOT / "scripts"))
        from embeddings import embed  # noqa: E402
        logger.info("embedding %d questions (once)", len(pool))
        _QVEC[key] = embed([q["question_polished"] for q in pool])
    return _QVEC[key]


def score_pool(idx_dir: Path, pool: List[Dict]) -> Dict[str, float]:
    """{qid: nDCG@10} in meta mode. Imports MetaIndex lazily so that callers
    that only read cached scores never pay for torch."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from retrieval import MetaIndex  # noqa: E402
    idx = MetaIndex(str(idx_dir))
    qv = query_vectors(pool)
    return {q["qid"]: ndcg_at_10([r for r, _ in idx.retrieve(
        q["question_polished"], mode="meta", skip_chunks=True, qvec=qv[i])[1]],
        q["work_key"]) for i, q in enumerate(pool)}


def by_type(scores: Dict[str, float], qtype: Dict[str, str],
            t: str) -> List[float]:
    return [v for qid, v in scores.items()
            if t == "overall" or qtype.get(qid) == t]


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


# ----------------------------------------------------------------- statistics

def bootstrap_ci(values: Sequence[float], n: int = 10000,
                 seed: int = 7) -> Tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    import numpy as np
    arr = np.asarray(values, dtype=float)
    gen = np.random.default_rng(seed)
    means = arr[gen.integers(0, len(arr), size=(n, len(arr)))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (float(lo), float(hi))


def perm_p(a: Sequence[float], b: Sequence[float], iters: int = 20000,
           seed: int = 11) -> float:
    """Paired permutation test (sign-flip), same estimator as
    permutation_fullpool.py so p-values stay comparable across the paper."""
    rng = random.Random(seed)
    d = [x - y for x, y in zip(a, b)]
    obs = abs(sum(d))
    cnt = sum(1 for _ in range(iters)
              if abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= obs)
    return (cnt + 1) / (iters + 1)


def paired(scores_a: Dict[str, float], scores_b: Dict[str, float],
           qtype: Dict[str, str], t: str) -> Tuple[List[float], List[float]]:
    ids = sorted(q for q in scores_a if q in scores_b
                 and (t == "overall" or qtype.get(q) == t))
    return [scores_a[q] for q in ids], [scores_b[q] for q in ids]


# ---------------------------------------------------------------------- pools

def question_pool(qa_path, keys: Optional[set] = None) -> List[Dict]:
    qa = read_jsonl(qa_path)
    return [q for q in qa if keys is None or q.get("work_key") in keys]


def cache(path: Path):
    """Tiny read-through cache for per-condition score dicts, so a re-run after
    a crash does not redo hours of scoring."""
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_cache(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))
