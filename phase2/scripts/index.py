#!/usr/bin/env python3
"""
index.py — Build the META-RAG dual index from the corpus.

Indexes:
  - chunks: full-text chunks (dense embeddings + BM25)
  - records: catalog records (dense embeddings over field text + field-boosted BM25)

Outputs (phase2/data/index/):
  chunk_ids.json, record_ids.json      (id -> metadata)
  chunk_emb.npy, record_emb.npy        (dense matrices)
  chunk_tokens.json, record_tokens.json (tokenized docs for BM25)
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


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def record_field_text(rec, fields="title+subj+ddc",
                      boost={"title": 1.5, "subjects": 2.0, "ddc": 1.0, "authors": 1.0}):
    """Concatenate fields with boost tags for BM25 scoring of catalog records.
    `fields` selects which metadata fields are included; authors are always
    kept, so "authors" is the no-metadata identity baseline. Any combination of
    title / subj / ddc is accepted (see field_ablation.py)."""
    parts = []
    if "title" in fields:
        parts += [rec.get("title") or ""] * int(boost["title"])
    if "subj" in fields:
        for s in (rec.get("subjects") or []):
            parts += [s] * int(boost["subjects"])
    if "ddc" in fields:
        for d in (rec.get("ddc") or []):
            parts.append(d)
    parts += [" ".join(rec.get("authors") or [])]
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus.jsonl"))
    ap.add_argument("--outdir", default=str(ROOT / "data" / "index"))
    ap.add_argument("--no-dense", action="store_true", help="skip dense embeddings (debug)")
    ap.add_argument("--fields", default="title+subj+ddc",
                    choices=["authors", "title", "subj", "ddc", "title+subj",
                             "title+ddc", "subj+ddc", "title+subj+ddc"],
                    help="which metadata fields the record index uses (field ablation)")
    ap.add_argument("--records-only", action="store_true",
                    help="reuse chunk side from --chunk-index; only (re)build the record side")
    ap.add_argument("--chunk-index", default=None, help="existing index dir to reuse chunk files from")
    args = ap.parse_args()

    with open(args.corpus, encoding="utf-8") as f:
        corpus = [json.loads(l) for l in f if l.strip()]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.records_only:
        # reuse chunk files (hardlink to save disk)
        src = Path(args.chunk_index)
        for name in ("chunk_ids.json", "chunk_tokens.pkl", "chunk_emb.npy",
                     "chunk_to_work.json"):
            if (src / name).exists() and not (outdir / name).exists():
                try:
                    (outdir / name).hardlink_to(src / name)
                except OSError:
                    import shutil
                    shutil.copy2(src / name, outdir / name)
        with open(outdir / "chunk_ids.json", encoding="utf-8") as f:
            n_chunks = len(json.load(f))
        print(f"[records-only] reusing {n_chunks} chunks from {src}")
    else:
        # ---- chunks ----
        chunk_ids, chunk_texts = [], []
        for rec in corpus:
            for c in rec.get("chunks", []):
                cid = c.get("chunk_id")
                if cid and "text" in c:
                    chunk_ids.append(cid)
                    chunk_texts.append(c["text"])
        with open(outdir / "chunk_ids.json", "w", encoding="utf-8") as f:
            json.dump(chunk_ids, f)
        with open(outdir / "chunk_tokens.pkl", "wb") as f:
            pickle.dump([tokenize(t) for t in chunk_texts], f)
        # chunk -> owning record, so retrieval can fuse chunk evidence into the
        # record ranking (see MetaIndex.retrieve, mode="meta")
        chunk_to_work = {c["chunk_id"]: rec["work_key"] for rec in corpus
                         for c in rec.get("chunks", []) if c.get("chunk_id")}
        with open(outdir / "chunk_to_work.json", "w", encoding="utf-8") as f:
            json.dump(chunk_to_work, f)

    # ---- records (fields-controlled) ----
    record_ids, record_field_texts = [], []
    for rec in corpus:
        record_ids.append(rec["work_key"])
        record_field_texts.append(record_field_text(rec, fields=args.fields))
    with open(outdir / "record_ids.json", "w", encoding="utf-8") as f:
        json.dump(record_ids, f)
    with open(outdir / "record_tokens.pkl", "wb") as f:
        pickle.dump([tokenize(t) for t in record_field_texts], f)

    # ---- dense ----
    if not args.no_dense and not args.records_only and chunk_texts:
        # Chunk embeddings were previously never built here; a fresh full index
        # came out with no chunk_emb.npy, which silently disabled dense and
        # hybrid retrieval.
        print(f"Embedding {len(chunk_texts)} chunks ...", flush=True)
        chunk_emb = embed(chunk_texts)
        np.save(outdir / "chunk_emb.npy", chunk_emb)
        print(f"chunk_emb: {chunk_emb.shape}")
    if not args.no_dense:
        print(f"Embedding {len(record_field_texts)} records [fields={args.fields}] ...")
        record_emb = embed(record_field_texts)
        np.save(outdir / "record_emb.npy", record_emb)
        print(f"record_emb: {record_emb.shape}")
    else:
        print("dense skipped (--no-dense)")

    print(f"Index written to {outdir}: records={len(record_ids)} [fields={args.fields}]")


if __name__ == "__main__":
    main()
