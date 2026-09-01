#!/usr/bin/env python3
"""
generate.py — Citation-grounded answer generation (META-RAG) + verification.

1. Builds a prompt from retrieved records (structured bibliographic context)
   and full-text chunks; the LLM (DeepSeek) must cite [REC:work_key] and/or
   [CHUNK:id] for every factual claim.
2. Verification module:
   - citation-exists: cited REC/CHUNK ids are in the retrieved set (and the index)
   - support: DeepSeek judge checks each claim against the cited sources
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "phase1" / "scripts"))
from llm_client import chat_text, chat_json  # noqa: E402

GEN_SYSTEM = (
    "You are a library discovery assistant. Answer the patron's question using ONLY the "
    "provided catalog records and full-text passages. Cite the source of every factual "
    "claim inline as [REC:work_key] for catalog records or [CHUNK:id] for passages. "
    "If the sources do not contain the answer, say so and cite nothing."
)

GEN_SYSTEM_NO_GROUNDING = (
    "You are a library discovery assistant. Answer the patron's question as helpfully "
    "as you can. You may draw on the provided context, but you are not required to cite "
    "sources or restrict yourself to them."
)


def build_prompt(question, records, chunks, grounding=True):
    rec_block = "\n".join(
        f"REC {r['work_key']}: title={r['title']!r}; subjects={r.get('subjects', [])}; "
        f"ddc={r.get('ddc', [])}; authors={r.get('authors', [])}"
        for r in records
    ) or "(no records retrieved)"
    chunk_block = "\n".join(f"CHUNK {c['chunk_id']}: {c['text'][:400]}" for c in chunks) or "(no passages retrieved)"
    if grounding:
        return f"""Question: {question}

Catalog records:
{rec_block}

Full-text passages:
{chunk_block}

Answer with inline citations, e.g. [REC:OL123W] or [CHUNK:2701-3]."""
    return f"""Question: {question}

Context:
{rec_block}

{chunk_block}

Answer the question."""


def parse_citations(answer):
    recs = set(re.findall(r"\[REC:([^\]]+)\]", answer))
    chunks = set(re.findall(r"\[CHUNK:([^\]]+)\]", answer))
    return recs, chunks


def norm_key(k):
    """Normalize record keys: '/works/OL123W' and 'OL123W' compare equal."""
    return k.strip().split("/")[-1]


def verify(answer, records, chunks, question=None, use_judge=True):
    """Return dict with citation checks + optional faithfulness judgment."""
    cited_recs, cited_chunks = parse_citations(answer)
    valid_recs = {norm_key(r["work_key"]) for r in records}
    valid_chunks = {c["chunk_id"] for c in chunks}
    rec_ok = {norm_key(c) for c in cited_recs} <= valid_recs if cited_recs else True
    chunk_ok = cited_chunks <= valid_chunks if cited_chunks else True
    all_verified = bool(cited_recs | cited_chunks) and rec_ok and chunk_ok
    judge = None
    if use_judge and answer:
        sources = [f"REC {r['work_key']}: {r['title']} {r.get('subjects', [])}" for r in records]
        sources += [f"CHUNK {c['chunk_id']}: {c['text'][:300]}" for c in chunks]
        try:
            resp = chat_json(
                f"Question: {question or '(not provided)'}\n\nAnswer: {answer}\n\n"
                f"Cited sources:\n" + "\n".join(sources) + "\n\n"
                "Is every claim in the answer supported by the cited sources? "
                'Respond {"faithful": true|false, "reason": "..."}',
                system=("You are a strict fact-checker for a library assistant."),
                temperature=0.0, max_tokens=200,
            )
            judge = bool(resp.get("faithful"))
        except Exception:
            judge = None
    return {
        "cited_recs": sorted(cited_recs), "cited_chunks": sorted(cited_chunks),
        "rec_citations_valid": rec_ok, "chunk_citations_valid": chunk_ok,
        "has_citations": bool(cited_recs | cited_chunks),
        "all_citations_verified": all_verified,
        "judge_faithful": judge,
    }


def extract_question(answer):
    return answer[:120]


def generate(question, records, chunks, model=None, grounding=True):
    prompt = build_prompt(question, records, chunks, grounding=grounding)
    system = GEN_SYSTEM if grounding else GEN_SYSTEM_NO_GROUNDING
    answer = chat_text(prompt, system=system, temperature=0.3, max_tokens=512, model=model)
    return answer


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", default="Find a book about whaling in the collection.")
    args = ap.parse_args()
    ans = generate(args.question, [], [])
    print(ans)
