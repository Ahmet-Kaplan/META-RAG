#!/usr/bin/env python3
"""
polish_qa_questions.py — Rewrite LIBRA-QA template questions into natural,
varied LLM wording via DeepSeek, WITHOUT changing their answerable intent
(gold answers are untouched and re-verified).

Pipeline:
  1. Load data/libra_qa_drafts.jsonl (template drafts).
  2. For each question, ask the LLM to rephrase it in natural human wording,
     constrained to keep the subject matter and answerability identical.
  3. Validate the reply (JSON {"question": "..."}); fall back to the original
     question on failure (counted).
  4. Checkpoint every 50 items; --resume skips already-polished qids.

Usage:
  python3 polish_qa_questions.py [--limit N] [--resume]
"""

import argparse
import json
import sys
import time
from pathlib import Path

from llm_client import chat_json

ROOT = Path(__file__).resolve().parent.parent

SYSTEM = (
    "You are a librarian helping to write natural-sounding evaluation questions "
    "for a library-search benchmark. You only rephrase; you never answer, never "
    "add or remove information, and never change what the correct answer is."
)

PROMPT = """Rephrase the following library-search question into natural, varied, human-like wording
(e.g., how a real patron would ask at a reference desk or in a chat search).

Constraints:
- Keep the SAME subject matter and the SAME intent (the correct answer must not change).
- Do NOT answer the question. Do NOT add new facts.
- Vary the phrasing; do not repeat the exact template wording.
- Respond ONLY with JSON: {{"question": "<your rephrasing>"}}

Question type: {qtype}
Original: {question}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", default=str(ROOT / "data" / "libra_qa_drafts.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "libra_qa_drafts_polished.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    with open(args.drafts, encoding="utf-8") as f:
        drafts = [json.loads(l) for l in f if l.strip()]
    if args.limit:
        drafts = drafts[: args.limit]

    done = {}
    if args.resume and Path(args.out).exists():
        for line in Path(args.out).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done[r["qid"]] = r
        print(f"Resuming: {len(done)} already polished")

    pending = [d for d in drafts if d["qid"] not in done]
    print(f"Polishing {len(pending)} of {len(drafts)} questions (est. cost < $0.10 @ deepseek-chat)...")

    polished, failures = [], 0
    # Concurrent: this is ~8.7k independent API calls, and serially it is hours.
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    counters = {"done": 0, "failed": 0}
    out_fh = open(args.out, "a" if args.resume else "w", encoding="utf-8")

    def polish_one(d):
        try:
            resp = chat_json(
                PROMPT.format(qtype=d["type"], question=d["question"]),
                system=SYSTEM, temperature=0.8, max_tokens=400,
            )
            new_q = (resp.get("question") or "").strip()
            if not new_q:
                raise ValueError("empty question")
        except Exception as e:
            new_q = d["question"]
            with lock:
                counters["failed"] += 1
            print(f"  [warn] {d['qid']}: fell back to template ({type(e).__name__})")
        rec = dict(d)
        rec["question_polished"] = new_q
        rec["polished"] = new_q != d["question"]
        with lock:
            polished.append(rec)
            out_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fh.flush()
            counters["done"] += 1
            if counters["done"] % 250 == 0:
                print(f"  polished {counters['done']}/{len(pending)}", flush=True)

    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(polish_one, pending))
        failures = counters["failed"]
    finally:
        out_fh.close()

    total = len(polished) + len(done)
    n_pol = sum(1 for r in polished if r["polished"]) + sum(1 for r in done.values() if r.get("polished"))
    print(f"\nDone: {total} questions; {n_pol} rephrased, {failures} fell back to template.")
    print(f"Output -> {args.out}")


if __name__ == "__main__":
    main()
