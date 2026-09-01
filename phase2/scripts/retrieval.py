#!/usr/bin/env python3
"""
retrieval.py — Hybrid metadata-aware retrieval for META-RAG.

Modes:
  dense   : dense over full-text chunks only
  bm25    : BM25 over full-text chunks only
  hybrid  : dense + BM25 over chunks (no metadata) [metadata-blind baseline]
  meta    : META-RAG — RRF over dense records + field-boosted BM25 records.
            Full-text chunks are retrieved in parallel and used as generation
            context, but do not enter the record ranking. [ours]
  meta4   : ablation — four-way RRF that additionally projects the dense- and
            BM25-chunk rankings onto their owning records and fuses them into
            the record ranking. Measured to be worse on topical discovery
            (see reports/fusion_fourway.json).

Fusion: reciprocal rank fusion (RRF).
"""

import argparse
import json
import pickle
import re
import sys
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from embeddings import embed  # noqa: E402

RRF_K = 60


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def rrf(rankings, k=RRF_K):
    """rankings: list of lists of ids (best first). Returns id -> score."""
    scores = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            scores[i] = scores.get(i, 0.0) + 1.0 / (k + rank + 1)
    return scores


def topk(scores, k):
    return sorted(scores.items(), key=lambda x: -x[1])[:k]


class MetaIndex:
    def __init__(self, index_dir, record_dir=None):
        d = Path(index_dir)
        rd = Path(record_dir) if record_dir else d
        self._norm_cache = {}
        self.chunk_ids = json.loads((d / "chunk_ids.json").read_text())
        self.record_ids = json.loads((rd / "record_ids.json").read_text())
        ctw = d / "chunk_to_work.json"
        self.chunk_to_work = json.loads(ctw.read_text()) if ctw.exists() else {}
        self.record_tokens = pickle.loads((rd / "record_tokens.pkl").read_bytes())
        self.bm25_records = BM25Okapi(self.record_tokens)
        # The chunk side is built lazily. Record-only evaluations never touch
        # it, and at ~460k chunks unpickling plus BM25 construction is minutes
        # of setup per index for nothing.
        self._chunk_dir = d
        self._chunk_tokens = None
        self._bm25_chunks = None
        # Load each dense matrix independently. Tying them together meant a
        # record index built without chunk embeddings silently dropped its
        # record embeddings too, degrading meta mode to BM25-only with no error.
        # record_emb is small and always needed; chunk_emb is ~700 MB at 460k
        # chunks and is untouched by record-only evaluation, so load it lazily.
        self._chunk_emb_path = d / "chunk_emb.npy"
        self._chunk_emb = None
        re_ = rd / "record_emb.npy"
        self.record_emb = np.load(re_) if re_.exists() else None

    @property
    def chunk_emb(self):
        if self._chunk_emb is None and self._chunk_emb_path.exists():
            self._chunk_emb = np.load(self._chunk_emb_path)
        return self._chunk_emb

    @property
    def chunk_tokens(self):
        if self._chunk_tokens is None:
            self._chunk_tokens = pickle.loads(
                (self._chunk_dir / "chunk_tokens.pkl").read_bytes())
        return self._chunk_tokens

    @property
    def bm25_chunks(self):
        if self._bm25_chunks is None:
            self._bm25_chunks = BM25Okapi(self.chunk_tokens)
        return self._bm25_chunks

    def _dense_rank(self, emb, ids, qvec, k):
        # cosine similarity: normalize both sides (dot product without
        # normalization is biased toward long/high-norm chunks at scale).
        # The row-normalized matrix is cached: it is query-independent, and
        # renormalizing 88k x 384 floats per query dominated runtime.
        key = id(emb)
        emb_n = self._norm_cache.get(key)
        if emb_n is None:
            emb_n = emb / np.linalg.norm(emb, axis=1, keepdims=True)
            self._norm_cache[key] = emb_n
        q_n = qvec / np.linalg.norm(qvec)
        sims = emb_n @ q_n
        order = np.argsort(-sims)[:k]
        return [ids[i] for i in order]

    def retrieve(self, query, mode="meta", topk_records=10, topk_chunks=5,
                 skip_chunks=False, qvec=None):
        """skip_chunks: for record-only scoring in meta mode. The record ranking
        never depends on the chunk rankings (they are fused separately, and only
        meta4 projects them in), so skipping chunk retrieval is exact -- it just
        avoids BM25 over every chunk in the collection.

        qvec: precomputed query embedding. The ablation sweeps score the same
        question pool against dozens of record indexes; embedding each question
        once per index dominated their runtime."""
        if mode in ("meta", "meta4", "hybrid", "dense", "bm25"):
            pass
        else:
            raise ValueError(f"unknown mode {mode}")
        q_tokens = tokenize(query)

        chunk_rankings = []
        want_chunks = not (skip_chunks and mode == "meta")
        if want_chunks and mode in ("dense", "hybrid", "meta", "meta4") and self.chunk_emb is not None:
            if qvec is None:
                qvec = embed([query])[0]
            chunk_rankings.append(self._dense_rank(self.chunk_emb, self.chunk_ids, qvec, 100))
        if want_chunks and mode in ("bm25", "hybrid", "meta", "meta4"):
            chunk_rankings.append(self.bm25_chunks.get_top_n(q_tokens, self.chunk_ids, n=100))

        record_rankings = []
        if mode in ("meta", "meta4"):
            if self.record_emb is not None:
                if qvec is None:
                    qvec = embed([query])[0]
                record_rankings.append(self._dense_rank(self.record_emb, self.record_ids, qvec, 50))
            record_rankings.append(self.bm25_records.get_top_n(q_tokens, self.record_ids, n=50))
            # meta4 only: project each chunk ranking onto its owning records
            # (best chunk rank wins) and fuse, giving a four-way RRF over dense
            # chunks, BM25 chunks, dense records, field-boosted BM25 records.
            # Measured to dilute the metadata signal on topical queries.
            if mode == "meta4" and self.chunk_to_work:
                record_rankings += [self._project_to_records(r) for r in chunk_rankings]

        chunks = topk(rrf(chunk_rankings), topk_chunks) if chunk_rankings else []
        records = topk(rrf(record_rankings), topk_records) if record_rankings else []
        return chunks, records

    def _project_to_records(self, chunk_ranking):
        """Chunk ranking -> record ranking, keeping each record's best chunk rank."""
        seen, out = set(), []
        for cid in chunk_ranking:
            wk = self.chunk_to_work.get(cid)
            if wk and wk not in seen:
                seen.add(wk)
                out.append(wk)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=str(ROOT / "data" / "index"))
    ap.add_argument("--query", default="find a book about whales and whaling")
    ap.add_argument("--mode", default="meta")
    args = ap.parse_args()
    idx = MetaIndex(args.index)
    chunks, records = idx.retrieve(args.query, mode=args.mode)
    print(f"[{args.mode}] top chunks: {[c for c, s in chunks]}")
    print(f"[{args.mode}] top records: {[r for r, s in records]}")


if __name__ == "__main__":
    main()
