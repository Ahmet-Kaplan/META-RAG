#!/usr/bin/env python3
"""
fig_pertype.py — Figure 2: per-type retrieval nDCG@10 grouped bar chart.

Reads the structured JSON written by phase2/scripts/evaluate.py
(reports/per_type_metrics.json, or --json path). Okabe-Ito colorblind-safe
palette; META-RAG highlighted. Saves figures/fig_pertype.pdf + .png.

Usage:
  python3 figures/fig_pertype.py [--json phase2/reports/per_type_metrics.json]
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent

OKABE = ["#E69F00", "#56B4E9", "#009E73", "#0072B2", "#D55E00", "#CC79A7", "#F0E442", "#000000"]
OUR_COLOR = "#D55E00"  # vermillion highlight for META-RAG
GRAY = "#8C8C8C"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "phase2" / "reports" / "per_type_metrics.json"))
    ap.add_argument("--out", default=str(ROOT / "figures" / "fig_pertype"))
    args = ap.parse_args()

    d = json.loads(Path(args.json).read_text())
    types = ["known_item", "topical", "bib_fact"]
    modes = ["dense", "bm25", "hybrid", "meta"]
    labels = {"known_item": "Known-item", "topical": "Topical", "bib_fact": "Bibliographic fact"}
    pvals = d.get("permutation", {})

    x = np.arange(len(types))
    n = len(modes)
    width = 0.72 / n
    fig, ax = plt.subplots(figsize=(3.5, 2.6))

    for i, m in enumerate(modes):
        scores = [d["per_type"][t][m] for t in types]
        color = OUR_COLOR if m == "meta" else GRAY
        hatch = "" if m == "meta" else ("//" if m == "hybrid" else ("\\\\" if m == "bm25" else ".."))
        bars = ax.bar(x + (i - n / 2 + 0.5) * width, scores, width * 0.92,
                      label="META-RAG (ours)" if m == "meta" else m,
                      color=color, edgecolor="white", linewidth=0.5, hatch=hatch)
        for bar, s in zip(bars, scores):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{s:.2f}", ha="center", va="bottom", fontsize=6.5, color="#333")

    ax.set_xticks(x)
    ax.set_xticklabels([labels[t] for t in types])
    ax.set_ylabel("nDCG@10")
    ax.set_ylim(0, 1.16)
    # legend BELOW the axes (no in-axes overlap)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4, fontsize=7)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)

    # significance annotations (meta vs hybrid) — direction-aware: only star
    # when meta > hybrid; otherwise mark "n.s." (or nothing if p not given)
    for i, t in enumerate(types):
        p = pvals.get(t)
        meta_v = d["per_type"][t]["meta"]
        hybrid_v = d["per_type"][t]["hybrid"]
        if p is None:
            continue

    fig.savefig(args.out + ".pdf")
    fig.savefig(args.out + ".png", dpi=300)
    print(f"saved {args.out}.pdf + .png")


if __name__ == "__main__":
    main()
