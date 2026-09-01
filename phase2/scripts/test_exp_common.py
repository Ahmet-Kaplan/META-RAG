#!/usr/bin/env python3
"""Self-check for the experiment plumbing. Runs the whole path on a tiny slice:
stub chunk index -> records-only index -> meta scoring -> stats.

  python3 phase2/scripts/test_exp_common.py
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exp_common as ec


def main() -> None:
    recs = ec.slim_corpus(ROOT / "data" / "corpus_scaled.jsonl",
                          ROOT / "data" / "slim_scaled.jsonl")[:40]
    keys = {r["work_key"] for r in recs}
    pool = ec.question_pool(ROOT.parent / "phase1" / "data" /
                            "libra_qa_drafts_scaled_polished.jsonl", keys)[:15]
    assert pool, "no questions matched the 40-record slice"
    qtype = {q["qid"]: q["type"] for q in pool}

    stub = ec.stub_chunk_index(ROOT / "data" / "index_selftest_stub")
    for tag in ("selftest_full", "selftest_nosubj"):
        shutil.rmtree(ROOT / "data" / f"index_{tag}", ignore_errors=True)

    full = ec.score_pool(ec.build_index(recs, "selftest_full", stub), pool)
    stripped = ec.score_pool(
        ec.build_index([ec.strip_meta(r) for r in recs], "selftest_nosubj", stub), pool)

    assert set(full) == {q["qid"] for q in pool}, "scored the wrong question set"
    assert all(0.0 <= v <= 1.0 for v in full.values()), "nDCG out of range"
    # a stub chunk index must not silently disable the record side
    assert ec.mean(list(full.values())) > 0.0, "no record ever retrieved"
    # stripping subject headings cannot help topical retrieval
    ft = ec.mean(ec.by_type(full, qtype, "topical"))
    st = ec.mean(ec.by_type(stripped, qtype, "topical"))
    assert ft >= st - 1e-9, f"stripping metadata improved topical retrieval ({st} > {ft})"

    again = ec.score_pool(ROOT / "data" / "index_selftest_full", pool)
    assert again == full, "scoring is not deterministic"

    a, b = ec.paired(full, stripped, qtype, "overall")
    assert len(a) == len(b) == len(full), "pairing dropped questions"
    assert 0.0 < ec.perm_p(a, a) <= 1.0, "permutation p out of range"
    lo, hi = ec.bootstrap_ci(list(full.values()), 200)
    assert lo <= ec.mean(list(full.values())) <= hi, "bootstrap CI excludes the mean"

    print(f"OK  n_q={len(pool)}  topical full={ft:.3f} stripped={st:.3f}")


if __name__ == "__main__":
    main()
