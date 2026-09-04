#!/usr/bin/env python3
"""
export_faithfulness_pilot.py — Build the human faithfulness-judgment workbook.

WHAT THIS IS FOR
RQ2 reports that an LLM judge rated N% of generated answers faithful to their
cited sources (gen_pass_scaled.json). The AIDL reviewer's last comment asks
for human validation of those LLM judgments. A human must read each
(question, answer, cited-sources) triple and decide whether the answer is
faithful — supported by the sources — exactly the decision the LLM judge made.

INPUT
The full answers were never persisted (evaluate.py kept only 5 examples), so
first regenerate the RQ2 answer set WITH persistence:

  cd phase2
  HF_HOME="$PWD/../.hf_cache" python3 scripts/evaluate.py \\
      --index data/index_scaled_ts \\
      --qa ../phase1/data/libra_qa_drafts_scaled_polished.jsonl \\
      --corpus data/corpus_scaled.jsonl \\
      --generate --questions 120 --mode meta \\
      --report reports/gen_pass_scaled.md \\
      --answers-out ../phase1/data/pilot/faithfulness/answers.jsonl

(rm the answers file first; --questions 120 with --mode meta replays the
shipped RQ2 pass. Cost: ~120 generation + ~120 judge calls, well under $1.)

This script then samples a stratified subset of the persisted answers — all
judge-unfaithful cases plus a random draw of judge-faithful ones — and writes
two blinded CSVs (one per labeler) plus items.jsonl with the LLM verdicts.

Outputs (phase1/data/pilot/faithfulness/):
  answers.jsonl   (input, from evaluate.py --answers-out)
  items.jsonl     id, question, answer, sources, llm_faithful
  labeler_A.csv   id, question, answer, sources (numbered), faithful? (blank)
  labeler_B.csv   same items, different order
  rubric.md       judging instructions

Usage:
  python3 phase1/scripts/export_faithfulness_pilot.py [--per-labeler 40] [--seed 7]
"""

import argparse
import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "pilot" / "faithfulness"

RUBRIC = """# Faithfulness judgment — instructions

For each item you are given:
  - the patron's QUESTION,
  - the assistant's ANSWER,
  - the SOURCES the answer cites ([REC ...] = catalog record, [CHUNK ...] =
    full-text passage). The sources are quoted exactly as the system retrieved
    them.

Decide: is the answer FAITHFUL — i.e., is every factual claim in the answer
supported by the cited sources?

Rules:
- Faithful (yes)  = every claim is supported by the cited sources.
- Unfaithful (no) = any claim is NOT supported: a source does not contain it,
  contradicts it, or the citation points to something that does not back the
  claim.
- Do not use outside knowledge to fill gaps: if the answer says something true
  in the world but the cited source does not say it, that is UNFAITHFUL.
- If the answer refuses to answer (e.g., "the sources do not contain this"),
  treat that as faithful — it made no unsupported claim.
- An answer with no citations at all is UNFAITHFUL unless it makes no claims.

Enter yes or no in the faithful column.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-labeler", type=int, default=40,
                    help="items per labeler (all unfaithful + random faithful)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--answers", default=str(OUT / "answers.jsonl"))
    args = ap.parse_args()

    answers_path = Path(args.answers)
    if not answers_path.exists():
        raise SystemExit(
            f"{answers_path} not found. First regenerate the RQ2 answers with "
            "persistence (see module docstring), then re-run this exporter.")

    answers = [json.loads(l) for l in answers_path.read_text().splitlines()
               if l.strip()]
    # only meta/grounded rows, where a judge verdict exists
    judged = [a for a in answers
              if a.get("judge_faithful") is not None and a.get("mode") == "meta"]
    if not judged:
        raise SystemExit("no meta rows with a judge verdict in answers file")
    print(f"{len(answers)} answers; {len(judged)} grounded+judged")

    unfaithful = [a for a in judged if not a["judge_faithful"]]
    faithful = [a for a in judged if a["judge_faithful"]]
    rng = random.Random(args.seed)
    n_f = max(0, args.per_labeler - len(unfaithful))
    rng.shuffle(faithful)
    sample = unfaithful + faithful[:n_f]
    rng.shuffle(sample)

    items = []
    for i, a in enumerate(sample, 1):
        items.append({
            "id": f"FID-{i:04d}",
            "qid": a.get("qid", ""),
            "question": a["question"],
            "answer": a["answer"],
            "sources": a.get("sources", []),
            "llm_faithful": bool(a["judge_faithful"]),
        })
    from collections import Counter
    print(f"sample: {len(items)} items "
          f"(LLM-faithful {sum(1 for x in items if x['llm_faithful'])} / "
          f"unfaithful {sum(1 for x in items if not x['llm_faithful'])})")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "items.jsonl").write_text(
        "\n".join(json.dumps(x) for x in items) + "\n")

    def write_csv(name, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "question", "answer", "sources", "faithful"])
            for r in rows:
                src = "\n".join(f"[{i}] {s}" for i, s in enumerate(r["sources"], 1))
                w.writerow([r["id"], r["question"], r["answer"], src, ""])

    write_csv("labeler_A.csv", items)
    order_b = items[:]
    rng.shuffle(order_b)
    write_csv("labeler_B.csv", order_b)
    (OUT / "rubric.md").write_text(RUBRIC)
    print(f"wrote {OUT/'labeler_A.csv'}, {OUT/'labeler_B.csv'}, rubric.md")


if __name__ == "__main__":
    main()
