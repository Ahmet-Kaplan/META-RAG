#!/usr/bin/env python3
"""
fig_robustness.py — Figure 3: metadata corruption sweep (degradation curve).

Reads reports/robustness.json. Line plot of nDCG@10 vs corruption rate for
overall / known_item / topical / bib_fact. Okabe-Ito palette; topical
highlighted. Saves figures/fig_robustness.pdf + .png.
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

COLORS = {"topical": "#D55E00", "overall": "#0072B2", "known_item": "#56B4E9", "bib_fact": "#009E73"}
MARKERS = {"topical": "o", "overall": "s", "known_item": "^", "bib_fact": "v"}
LABELS = {"topical": "Topical (subjects-driven)", "overall": "Overall",
          "known_item": "Known-item", "bib_fact": "Bibliographic fact"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "phase2" / "reports" / "robustness.json"))
    ap.add_argument("--out", default=str(ROOT / "figures" / "fig_robustness"))
    args = ap.parse_args()

    d = json.loads(Path(args.json).read_text())
    rates = d["rates"]
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for key in ("topical", "overall", "known_item", "bib_fact"):
        vals = [d["per_type"][str(r)][key] if key != "overall" else d["overall"][str(r)] for r in rates]
        ax.plot(rates, vals, label=LABELS[key], color=COLORS[key],
                marker=MARKERS[key], markersize=4, lw=1.8, zorder=3)
    ax.axhline(0.283, color="#888888", ls=":", lw=1.2)
    ax.set_xlabel("Metadata corruption rate")
    ax.set_ylabel("nDCG@10")
    ax.set_xticks(rates)
    ax.set_xticklabels([f"{r:.0%}" for r in rates])
    ax.set_ylim(0.1, 1.02)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    # legend BELOW the axes (no in-axes overlap with the annotation/lines)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=4, fontsize=7)

    fig.savefig(args.out + ".pdf")
    fig.savefig(args.out + ".png", dpi=300)
    print(f"saved {args.out}.pdf + .png")


if __name__ == "__main__":
    main()
