#!/usr/bin/env python3
"""
field_ablation.py — Which catalog field carries the topical retrieval signal?

META-RAG indexes title + subject headings + DDC (authors are always present as
the identity baseline). The paper reports the bundle. A bundle is not a
finding: a library deciding what to spend cataloging effort on needs to know
which field does the work.

Eight record indexes are built over the same collection, differing only in
which metadata fields enter the record text, and each is scored on the whole
in-corpus question pool:

  authors            identity baseline (no title, no subject access)
  title              what a bare inventory list gives you
  subj / ddc         each subject-access field alone
  title+subj, title+ddc, subj+ddc
  title+subj+ddc     full (= the paper's META-RAG record index)

Marginal contribution of a field = full - (full without that field), which is
the quantity a cataloging budget actually buys.

Outputs:
  phase2/reports/field_ablation.json + .md

Usage:
  python3 phase2/scripts/field_ablation.py
"""

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import exp_common as ec  # noqa: E402

logger = logging.getLogger(__name__)

# label -> fields string handed to index.py (authors are always included)
CONFIGS = {
    "authors": "authors",
    "title": "title",
    "subj": "subj",
    "ddc": "ddc",
    "title+subj": "title+subj",
    "title+ddc": "title+ddc",
    "subj+ddc": "subj+ddc",
    "full": "title+subj+ddc",
}
# marginal contribution of a field = full - the config that drops only it
MARGINALS = {"subj": "title+ddc", "ddc": "title+subj", "title": "subj+ddc"}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(ROOT / "data" / "corpus_scaled.jsonl"))
    ap.add_argument("--chunk-index", default=str(ROOT / "data" / "index_scaled"))
    ap.add_argument("--qa", default=str(ROOT.parent / "phase1" / "data" /
                                        "libra_qa_drafts_scaled_polished.jsonl"))
    ap.add_argument("--bootstrap", type=int, default=10000)
    ap.add_argument("--iters", type=int, default=20000)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    records = ec.slim_corpus(Path(args.corpus),
                             ROOT / "data" / f"slim{args.tag or '_scaled'}.jsonl")
    keys = {r["work_key"] for r in records}
    pool = ec.question_pool(args.qa, keys)
    qtype = {q["qid"]: q["type"] for q in pool}
    logger.info("%d records, %d in-corpus questions", len(records), len(pool))

    cache_path = ROOT / "reports" / f"field_ablation_per_question{args.tag}.json"
    per_q = ec.cache(cache_path)
    for label, fields in CONFIGS.items():
        if label in per_q:
            continue
        idx = ec.build_index(records, f"fa_{label.replace('+', '_')}{args.tag}",
                             Path(args.chunk_index), fields=fields)
        per_q[label] = ec.score_pool(idx, pool)
        ec.save_cache(per_q, cache_path)
        logger.info("%-14s overall=%.3f topical=%.3f", label,
                    ec.mean(ec.by_type(per_q[label], qtype, "overall")),
                    ec.mean(ec.by_type(per_q[label], qtype, "topical")))

    out = {"n_records": len(records), "n_questions": len(pool),
           "bootstrap": args.bootstrap, "perm_iters": args.iters,
           "configs": {}, "marginals": {}}

    for label in CONFIGS:
        entry = {}
        for t in (*ec.TYPES, "overall"):
            vals = ec.by_type(per_q[label], qtype, t)
            lo, hi = ec.bootstrap_ci(vals, args.bootstrap)
            entry[t] = {"n": len(vals), "mean": round(ec.mean(vals), 3),
                        "ci95": [round(lo, 3), round(hi, 3)]}
            if label != "full":
                a, b = ec.paired(per_q["full"], per_q[label], qtype, t)
                entry[t]["p_vs_full"] = round(ec.perm_p(a, b, args.iters), 5)
        out["configs"][label] = entry

    for field, without in MARGINALS.items():
        m = {}
        for t in (*ec.TYPES, "overall"):
            a, b = ec.paired(per_q["full"], per_q[without], qtype, t)
            diffs = [x - y for x, y in zip(a, b)]
            lo, hi = ec.bootstrap_ci(diffs, args.bootstrap)
            m[t] = {"n": len(diffs), "gain": round(ec.mean(diffs), 3),
                    "ci95": [round(lo, 3), round(hi, 3)],
                    "p": round(ec.perm_p(a, b, args.iters), 5)}
        out["marginals"][field] = {"dropped_from": "full", "compared_to": without, **m}

    (ROOT / "reports" / f"field_ablation{args.tag}.json").write_text(json.dumps(out, indent=2))

    md = ["# Field ablation: which catalog field carries the signal?", "",
          f"- {len(records)} records, full in-corpus pool ({len(pool)} questions), meta mode",
          f"- Bootstrap 95% CIs ({args.bootstrap:,} resamples); paired permutation "
          f"vs. `full` ({args.iters:,} sign-flips)",
          "- Authors are present in every configuration (identity baseline)", "",
          "| Fields indexed | known_item | topical | bib_fact | overall | p vs full (topical) |",
          "|---|---|---|---|---|---|"]
    for label, e in out["configs"].items():
        cells = " | ".join(f"{e[t]['mean']:.3f} [{e[t]['ci95'][0]:.3f}, {e[t]['ci95'][1]:.3f}]"
                           for t in (*ec.TYPES, "overall"))
        p = e["topical"].get("p_vs_full")
        md.append(f"| {label} | {cells} | {'--' if p is None else f'{p:.4f}'} |")
    md += ["", "## Marginal contribution of each field", "",
           "Gain from adding the field to the other two (`full` minus the "
           "configuration that drops only it).", "",
           "| Field | topical gain | 95% CI | p | overall gain |", "|---|---|---|---|---|"]
    for field, m in out["marginals"].items():
        t, o = m["topical"], m["overall"]
        md.append(f"| {field} | **{t['gain']:+.3f}** | [{t['ci95'][0]:+.3f}, "
                  f"{t['ci95'][1]:+.3f}] | {t['p']:.4f} | {o['gain']:+.3f} |")
    (ROOT / "reports" / f"field_ablation{args.tag}.md").write_text("\n".join(md) + "\n")

    # paper macros
    def cmd(n, v):
        return r"\newcommand{" + n + r"}{" + str(v) + "}"

    def fmt_p(p):
        return r"$p<0.001$" if p < 0.001 else f"$p={p:.3f}$"

    c, mg = out["configs"], out["marginals"]

    def gain_ci(f):
        lo, hi = mg[f]["topical"]["ci95"]
        return f"[{lo:+.3f}, {hi:+.3f}]"

    tex = [f"% ablation_numbers.tex - AUTO-GENERATED by field_ablation.py "
           f"(full pool, n={len(pool)}).",
           cmd(r"\AblSubjGain", f"{mg['subj']['topical']['gain']:+.3f}"),
           cmd(r"\AblSubjCI", gain_ci("subj")),
           cmd(r"\AblSubjP", fmt_p(mg["subj"]["topical"]["p"])),
           cmd(r"\AblDdcGain", f"{mg['ddc']['topical']['gain']:+.3f}"),
           cmd(r"\AblDdcCI", gain_ci("ddc")),
           cmd(r"\AblDdcP", fmt_p(mg["ddc"]["topical"]["p"])),
           cmd(r"\AblTitleGain", f"{mg['title']['topical']['gain']:+.3f}"),
           cmd(r"\AblTitleCI", gain_ci("title")),
           cmd(r"\AblTitleP", fmt_p(mg["title"]["topical"]["p"])),
           cmd(r"\AblTitleSubjTopical", f"{c['title+subj']['topical']['mean']:.3f}"),
           cmd(r"\AblFullTopical", f"{c['full']['topical']['mean']:.3f}"),
           cmd(r"\AblSubjOnlyTopical", f"{c['subj']['topical']['mean']:.3f}"),
           cmd(r"\AblSubjOnlyKnown", f"{c['subj']['known_item']['mean']:.3f}"),
           cmd(r"\AblTitleOnlyTopical", f"{c['title']['topical']['mean']:.3f}"),
           cmd(r"\AblTitleOnlyKnown", f"{c['title']['known_item']['mean']:.3f}"),
           cmd(r"\AblAuthorsTopical", f"{c['authors']['topical']['mean']:.3f}"),
           cmd(r"\AblNQ", f"{len(pool):,}".replace(",", "{,}")),
           # per-type marginals: the prose cites the known-item cost of subject
           # headings and the bib_fact credit for DDC, which were hardcoded
           cmd(r"\AblSubjKnownGain", f"{mg['subj']['known_item']['gain']:+.3f}"),
           cmd(r"\AblSubjKnownP", fmt_p(mg["subj"]["known_item"]["p"])),
           cmd(r"\AblDdcBibGain", f"{mg['ddc']['bib_fact']['gain']:+.3f}"),
           cmd(r"\AblDdcBibP", fmt_p(mg["ddc"]["bib_fact"]["p"]))]
    (ROOT.parent / "paper" / "ablation_numbers.tex").write_text("\n".join(tex) + "\n")

    # configuration table
    order = ["authors", "title", "subj", "ddc", "title+subj", "title+ddc",
             "subj+ddc", "full"]
    pretty = {"authors": "authors only", "title": "$+$title", "subj": "$+$subj",
              "ddc": "$+$DDC", "title+subj": r"$+$title$+$subj",
              "title+ddc": "$+$title$+$DDC", "subj+ddc": "$+$subj$+$DDC",
              "full": r"\textbf{title$+$subj$+$DDC}"}
    body = []
    for lab in order:
        e = c[lab]
        cells = " & ".join(
            (f"\\textbf{{{e[t]['mean']:.3f}}}" if lab == "title+subj" and t == "topical"
             else f"{e[t]['mean']:.3f}") for t in (*ec.TYPES, "overall"))
        body.append(f"{pretty[lab]} & {cells} \\\\")
    (ROOT.parent / "paper" / "ablation_table.tex").write_text(
        f"% ablation_table.tex - AUTO-GENERATED by field_ablation.py (n={len(pool)}).\n"
        "\\begin{tabular}{lcccc}\n\\toprule\nRecord fields & known\\_item & topical & "
        "bib\\_fact & overall \\\\\n\\midrule\n" + "\n".join(body) +
        "\n\\bottomrule\n\\end{tabular}\n")

    # marginal-contribution table
    rows = []
    for f_, lab in (("title", "title"), ("subj", "subject headings"), ("ddc", "DDC")):
        cells = " & ".join(
            f"{mg[f_][t]['gain']:+.3f}" + (r"$^{*}$" if mg[f_][t]["p"] < 0.05 else "")
            for t in (*ec.TYPES, "overall"))
        rows.append(f"{lab} & {cells} & {gain_ci(f_)} \\\\")
    (ROOT.parent / "paper" / "ablation_marginals.tex").write_text(
        f"% ablation_marginals.tex - AUTO-GENERATED by field_ablation.py (n={len(pool)}).\n"
        "\\begin{tabular}{lccccc}\n\\toprule\nField & known\\_item & topical & "
        "bib\\_fact & overall & topical 95\\% CI \\\\\n\\midrule\n" +
        "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
