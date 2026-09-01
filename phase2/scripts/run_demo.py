#!/usr/bin/env python3
"""
run_demo.py — End-to-end META-RAG demo: corpus (30 books) -> index -> eval.

Usage:
  HF_HOME="$PWD/../.hf_cache" python3 scripts/run_demo.py [--questions 20]
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(script, *args):
    cmd = [PY, str(ROOT / "scripts" / script), *args]
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", type=int, default=30)
    ap.add_argument("--questions", type=int, default=20)
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--no-dense", action="store_true")
    args = ap.parse_args()

    r = run("corpus.py", f"--limit {args.books}")
    if r.returncode != 0:
        sys.exit(r.returncode)
    dense = ["--no-dense"] if args.no_dense else []
    run("index.py", *dense)
    gen = ["--generate"] if args.generate else []
    run("evaluate.py", "--all-modes", f"--questions {args.questions}", *gen)
    print("\nDemo complete. See phase2/reports/eval_summary.json")


if __name__ == "__main__":
    main()
