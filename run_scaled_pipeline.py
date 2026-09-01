#!/usr/bin/env python3
"""
run_scaled_pipeline.py — ONE command to run the full LIBRA-Eval/META-RAG
pipeline at scale on your machine.

Steps (checkpointed; resumes automatically, --force to redo):
  1. gutenberg  expand Gutenberg index (gutendex)          -> phase1/data/gutenberg_index_scaled.jsonl
  2. join       Gutenberg <-> OpenLibrary fuzzy join       -> phase1/data/join_matches_scaled.jsonl
  3. libra_cat  build LIBRA-CAT (target 600, LCSH+DDC)     -> phase1/data/libra_cat_records_scaled.jsonl
  4. qa         build LIBRA-QA template drafts             -> phase1/data/libra_qa_drafts_scaled.jsonl
  5. polish     LLM-polish QA questions (needs .env key)   -> phase1/data/libra_qa_drafts_scaled_polished.jsonl
  6. corpus     download Gutenberg full texts + chunks     -> phase2/data/corpus_scaled.jsonl
  7. index      dual index (dense + BM25)                  -> phase2/data/index_scaled/
  8. evaluate   per-type metrics across all 4 modes        -> phase2/reports/per_type_metrics_scaled.md

Usage:
  python3 run_scaled_pipeline.py                      # everything (polish skipped w/o key)
  python3 run_scaled_pipeline.py --polish             # include LLM polish (needs phase1/.env)
  python3 run_scaled_pipeline.py --steps join,corpus  # run only these steps
  python3 run_scaled_pipeline.py --force              # redo everything from scratch
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
STATE = ROOT / ".scaled_state.json"
HF_HOME = ROOT / ".hf_cache"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def save_state(state):
    STATE.write_text(json.dumps(state, indent=2))


def run(step, cmd, cwd, env_extra=None):
    env = dict(os.environ)
    env["HF_HOME"] = str(HF_HOME)
    env["TRANSFORMERS_CACHE"] = str(HF_HOME)
    if env_extra:
        env.update(env_extra)
    print(f"\n=== [{step}] {time.strftime('%H:%M:%S')} ===\n$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=env)
    dur = round(time.time() - t0, 1)
    print(f"--- [{step}] finished in {dur}s (rc={r.returncode}) ---", flush=True)
    return r.returncode == 0, dur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-books", type=int, default=4000)
    ap.add_argument("--join-sample", type=int, default=2000)
    ap.add_argument("--corpus-books", type=int, default=250)
    ap.add_argument("--qa-max", type=int, default=1200)
    ap.add_argument("--eval-questions", type=int, default=300)
    ap.add_argument("--polish", action="store_true", help="run LLM polish (needs phase1/.env)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--steps", default="gutenberg,join,libra_cat,qa,corpus,index,evaluate",
                    help="comma-separated subset; 'polish' included only with --polish")
    args = ap.parse_args()

    state = load_state()
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]

    def want(step):
        return step in steps and (args.force or not state.get(step, {}).get("ok"))

    p1 = ROOT / "phase1"
    p2 = ROOT / "phase2"

    # 1. gutenberg index
    if want("gutenberg"):
        ok, d = run("gutenberg", [PY, "scripts/fetch_gutenberg_index.py",
                                  "--max-books", str(args.index_books),
                                  "--out", "data/gutenberg_index_scaled.jsonl"], p1)
        state["gutenberg"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit(f"step gutenberg failed")

    # 2. join
    if want("join"):
        ok, d = run("join", [PY, "scripts/join_pilot.py",
                             "--index", "data/gutenberg_index_scaled.jsonl",
                             "--sample", str(args.join_sample),
                             "--out", "data/join_matches_scaled.jsonl",
                             "--report", "reports/join_scaled_report.md"], p1)
        state["join"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit("step join failed")

    # 3. libra_cat
    if want("libra_cat"):
        ok, d = run("libra_cat", [PY, "scripts/build_libra_cat.py",
                                  "--matches", "data/join_matches_scaled.jsonl",
                                  "--target", "600",
                                  "--out", "data/libra_cat_records_scaled.jsonl"], p1)
        state["libra_cat"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit("step libra_cat failed")

    # 4. qa drafts
    if want("qa"):
        ok, d = run("qa", [PY, "scripts/build_qa_drafts.py",
                           "--matches", "data/join_matches_scaled.jsonl",
                           "--max-questions", str(args.qa_max),
                           "--out", "data/libra_qa_drafts_scaled.jsonl"], p1)
        state["qa"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit("step qa failed")

    # 5. polish (optional)
    qa_for_eval = "data/libra_qa_drafts_scaled_polished.jsonl"
    if args.polish and (args.force or not state.get("polish", {}).get("ok")):
        if not (p1 / ".env").exists():
            print("Skipping polish: phase1/.env with DEEPSEEK_API_KEY not found.")
            qa_for_eval = "data/libra_qa_drafts_scaled.jsonl"
        else:
            ok, d = run("polish", [PY, "scripts/polish_qa_questions.py",
                                   "--drafts", "data/libra_qa_drafts_scaled.jsonl",
                                   "--out", "data/libra_qa_drafts_scaled_polished.jsonl",
                                   "--resume"], p1)
            state["polish"] = {"ok": ok, "sec": d}
            save_state(state)
            if not ok:
                print("polish step failed; continuing with unpolished drafts")
                qa_for_eval = "data/libra_qa_drafts_scaled.jsonl"
    else:
        qa_for_eval = "data/libra_qa_drafts_scaled_polished.jsonl" if (p1 / "data" / "libra_qa_drafts_scaled_polished.jsonl").exists() else "data/libra_qa_drafts_scaled.jsonl"

    # 6. corpus
    if want("corpus"):
        ok, d = run("corpus", [PY, "scripts/corpus.py",
                               "--matches", "../phase1/data/join_matches_scaled.jsonl",
                               "--limit", str(args.corpus_books),
                               "--out", "data/corpus_scaled.jsonl"], p2)
        state["corpus"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit("step corpus failed")

    # 7. index
    if want("index"):
        ok, d = run("index", [PY, "scripts/index.py",
                              "--corpus", "data/corpus_scaled.jsonl",
                              "--outdir", "data/index_scaled"], p2)
        state["index"] = {"ok": ok, "sec": d}
        save_state(state)
        if not ok:
            sys.exit("step index failed")

    # 8. evaluate
    if want("evaluate"):
        ok, d = run("evaluate", [PY, "scripts/evaluate.py",
                                 "--index", "data/index_scaled",
                                 "--qa", f"../phase1/{qa_for_eval}",
                                 "--corpus", "data/corpus_scaled.jsonl",
                                 "--all-modes",
                                 "--questions", str(args.eval_questions),
                                 "--report", "reports/per_type_metrics_scaled.md"], p2)
        state["evaluate"] = {"ok": ok, "sec": d}
        save_state(state)

    # summary
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    for s in ["gutenberg", "join", "libra_cat", "qa", "polish", "corpus", "index", "evaluate"]:
        st = state.get(s)
        if st:
            print(f"  {s:<10} {'OK' if st.get('ok') else 'FAIL'}  ({st.get('sec', '?')}s)")
    print("\nKey outputs:")
    print("  phase1/data/libra_cat_records_scaled.jsonl     (LIBRA-CAT, target 600)")
    print("  phase1/data/libra_qa_drafts_scaled_polished.jsonl (LIBRA-QA)")
    print("  phase2/data/corpus_scaled.jsonl                (retrieval corpus)")
    print("  phase2/reports/per_type_metrics_scaled.md      (per-type results)")
    print(f"\nRun with --polish to include LLM question polish (est. <$0.20 for {args.qa_max} questions).")


if __name__ == "__main__":
    main()
