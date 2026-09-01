#!/usr/bin/env python3
"""
judge_pilot.py — LLM-judge vs. human faithfulness agreement pilot (RQ-risk check).

Purpose: before trusting an LLM judge to score answer faithfulness at scale,
measure agreement with human labels on a small gold subset.

Usage (after setting an LLM API key — see phase1/README.md):
  python3 judge_pilot.py --answers answers.jsonl --human-labels labels.jsonl

Input formats:
  answers.jsonl:  {"id": ..., "question": ..., "answer": ..., "citations": [...]}
  labels.jsonl:   {"id": ..., "human_faithful": true/false}

The script calls the LLM judge (stub below — plug your provider), computes
Cohen's kappa between LLM-judge and human labels, and prints the verdict.
"""

import argparse
import json
import sys

from llm_client import chat_json

JUDGE_SYSTEM = (
    "You are a strict fact-checker for a library-search assistant. "
    "You decide whether an answer's claims are supported by its cited sources."
)

JUDGE_PROMPT = """Question: {question}

Answer: {answer}

Cited sources (retrieved passages / catalog records):
{citations}

Check whether EVERY factual claim in the answer is supported by the cited sources.
A claim is unsupported if a source does not contain it, contradicts it, or the
citation does not exist. Do not use outside knowledge to fill gaps.
Respond ONLY with JSON: {{"faithful": true|false, "reason": "<one sentence>"}}"""


def llm_judge(question, answer, citations):
    """Return True iff the LLM judge deems the answer faithful to its citations."""
    if not citations:
        return False
    cite_block = "\n".join(f"- {c[:500]}" for c in citations)
    try:
        resp = chat_json(
            JUDGE_PROMPT.format(question=question, answer=answer[:3000], citations=cite_block),
            system=JUDGE_SYSTEM, temperature=0.0, max_tokens=300,
        )
        return bool(resp.get("faithful"))
    except Exception as e:
        print(f"  [warn] judge call failed: {type(e).__name__}", file=sys.stderr)
        return False


def kappa(a, b):
    """Cohen's kappa for two binary label lists."""
    n = len(a)
    assert n == len(b)
    both = sum(1 for x, y in zip(a, b) if x == y)
    p_o = both / n
    p_a = (sum(a) / n) * (sum(b) / n) + (1 - sum(a) / n) * (1 - sum(b) / n)
    return (p_o - p_a) / (1 - p_a) if p_a < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--human-labels", required=True)
    args = ap.parse_args()

    with open(args.answers, encoding="utf-8") as f:
        answers = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    with open(args.human_labels, encoding="utf-8") as f:
        humans = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}

    ids = sorted(set(answers) & set(humans))
    print(f"Evaluating {len(ids)} items with both human and LLM-judge labels...")

    llm, hum = [], []
    for i, qid in enumerate(ids):
        a = answers[qid]
        l = llm_judge(a["question"], a["answer"], a.get("citations", []))
        llm.append(l)
        hum.append(bool(humans[qid]["human_faithful"]))
        if (i + 1) % 10 == 0:
            print(f"  judged {i + 1}/{len(ids)}")
        # rate limiting: add sleep if needed

    k = kappa(llm, hum)
    agree = sum(1 for x, y in zip(llm, hum) if x == y) / len(ids)
    print(f"\nLLM-judge vs human agreement: {agree:.2%}")
    print(f"Cohen's kappa: {k:.3f}")
    if k >= 0.7:
        print("Verdict: judge correlates well enough — safe to use at scale (re-check on new domains).")
    elif k >= 0.4:
        print("Verdict: moderate agreement — use judge with calibrated thresholds and human spot-checks.")
    else:
        print("Verdict: poor agreement — do NOT use the LLM judge; fall back to retrieval metrics + human sample.")


if __name__ == "__main__":
    main()
