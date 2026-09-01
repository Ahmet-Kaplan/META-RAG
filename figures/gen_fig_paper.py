#!/usr/bin/env python3
"""
gen_fig_paper.py — Regenerate Fig 2 (per-type) and Fig 3 (robustness) FROM
the paper's own number files, so figures always match the current paper.

Reads:
  paper/table1.tex                     (full-pool per-type nDCG@10)
  paper/noise_numbers.tex              (full-pool corruption sweep)
  paper/ablation_table.tex             (title-only topical reference line)
  phase2/reports/permutation_fullpool.json  (meta-vs-hybrid p-values)

Outputs figures/fig_pertype.{pdf,png} and figures/fig_robustness.{pdf,png}
"""

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 9, "legend.fontsize": 7.5, "legend.frameon": False,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
})
OUR_COLOR = "#D55E00"
GRAY = "#8C8C8C"
COLORS = {"topical": "#D55E00", "overall": "#0072B2", "known_item": "#56B4E9", "bib_fact": "#009E73"}
MARKERS = {"topical": "o", "overall": "s", "known_item": "^", "bib_fact": "v"}
LABELS = {"topical": "Topical (subjects-driven)", "overall": "Overall",
          "known_item": "Known-item", "bib_fact": "Bibliographic fact"}
TYPES = ["known_item", "topical", "bib_fact"]
MODES = ["dense", "bm25", "hybrid", "meta"]


def parse_rows(tex_path):
    rows = {}
    for line in tex_path.read_text(encoding="utf-8").splitlines():
        line = line.replace("\\textbf{", "").replace("}", "")
        m = re.match(r"^\s*([a-z_\\]+) & ([\d.]+) & ([\d.]+) & ([\d.]+) & ([\d.]+)", line)
        if m:
            rows[m.group(1).replace("\\_", "_")] = [float(x) for x in m.groups()[1:]]
    return rows


def parse_noise(tex_path):
    rate_map = {"Zero": 0.0, "TwentyFive": 0.25, "Fifty": 0.5, "SeventyFive": 0.75, "Hundred": 1.0}
    pat = re.compile(r"\\newcommand\{\\Noise(Zero|TwentyFive|Fifty|SeventyFive|Hundred)(Topical|Overall|Known|Bib)\}\{([\d.]+)\}")
    out = {}
    for m in pat.finditer(tex_path.read_text(encoding="utf-8")):
        rate, field, val = m.group(1), m.group(2), float(m.group(3))
        out.setdefault(field.lower(), {})[rate_map[rate]] = val
    return out


def title_only_topical(tex_path):
    for line in tex_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*\$\+\$title & ([\d.]+) & ([\d.]+) & ([\d.]+) & ([\d.]+)", line)
        if m:
            return float(m.group(2))  # topical column
    return None


def parse_macro_pairs(tex_path, prefix, names):
    """Parse \newcommand{\<prefix><Name>}{<value>} for a set of names."""
    out = {}
    pat = re.compile(r"\\newcommand\{\\" + prefix + r"(" + "|".join(names) + r")\}\{([\d.]+)\}")
    for m in pat.finditer(tex_path.read_text(encoding="utf-8")):
        out[m.group(1)] = float(m.group(2))
    return out


def fig_sparsity(p, outdir):
    levels_names = ("Zero", "TwentyFive", "Fifty", "SeventyFive", "Hundred")
    names = [f"{f}{l}" for f in ("Base", "Enr") for l in levels_names]
    vals = parse_macro_pairs(p / "sparsity_numbers.tex", "Sp", names)
    levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    base = [vals[f"Base{l}"] for l in levels_names]
    enr = [vals[f"Enr{l}"] for l in levels_names]
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    ax.plot(levels, base, label="Catalog without subjects (title-only)",
            color="#56B4E9", marker="^", markersize=4, lw=1.8, zorder=3)
    ax.plot(levels, enr, label="+ LLM-enriched subject headings",
            color=OUR_COLOR, marker="o", markersize=4, lw=1.8, zorder=3)
    ax.fill_between(levels, base, enr, color=OUR_COLOR, alpha=0.12, zorder=2)
    for i, lvl in enumerate(levels):
        ax.text(lvl, enr[i] + 0.03, f"+{enr[i]-base[i]:.2f}", ha="center", fontsize=6.5, color=OUR_COLOR)
    ax.set_xlabel("Records with subject coverage")
    ax.set_ylabel("Topical nDCG@10")
    ax.set_xticks(levels)
    ax.set_xticklabels([f"{l:.0%}" for l in levels])
    ax.set_ylim(0.2, 0.95)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7)
    fig.savefig(outdir / "fig_sparsity.pdf")
    fig.savefig(outdir / "fig_sparsity.png", dpi=300)
    print("saved figures/fig_sparsity.pdf + .png")


def fig_loop(p, outdir):
    names = [f"{c}{m}" for c in ("None", "Llm", "LlmMatched", "Gold")
             for m in ("Topical", "Overall", "Known", "Bib")]
    vals = parse_macro_pairs(p / "loop_numbers.tex", "Loop", names)
    conditions = [("None", "None", "no subject metadata"),
                  ("Llm", "LLM", "+ LLM metadata"),
                  ("Gold", "Gold", "gold metadata")]
    metrics = [("Topical", "Topical"), ("Overall", "Overall")]
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    x = np.arange(len(conditions))
    width = 0.38
    for j, (mkey, mlabel) in enumerate(metrics):
        scores = [vals[c + mkey] for c, _, _ in conditions]
        ax.bar(x + (j - 0.5) * width, scores, width * 0.9,
               label=mlabel, color=OUR_COLOR if mkey == "Topical" else "#0072B2",
               edgecolor="white", linewidth=0.5)
        for xi, s in zip(x, scores):
            ax.text(xi + (j - 0.5) * width, s + 0.015, f"{s:.2f}",
                    ha="center", va="bottom", fontsize=6.5, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{disp}\n{subl}" for _, disp, subl in conditions], fontsize=7.5)
    ax.set_ylabel("nDCG@10")
    ax.set_ylim(0, 0.95)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=2, fontsize=7)
    fig.savefig(outdir / "fig_loop.pdf")
    fig.savefig(outdir / "fig_loop.png", dpi=300)
    print("saved figures/fig_loop.pdf + .png")


def main():
    p = ROOT / "paper"
    rows = parse_rows(p / "table1.tex")
    noise = parse_noise(p / "noise_numbers.tex")
    title_topical = title_only_topical(p / "ablation_table.tex")
    perm = json.loads((ROOT / "phase2" / "reports" / "permutation_fullpool.json").read_text())
    pvals = {t: perm["meta_vs_hybrid"][t]["p"] for t in TYPES}

    # ---------------- Figure 2: per-type grouped bars ----------------
    x = np.arange(len(TYPES))
    n = len(MODES)
    width = 0.72 / n
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for i, mode in enumerate(MODES):
        scores = [rows[t][i] for t in TYPES]
        color = OUR_COLOR if mode == "meta" else GRAY
        hatch = "" if mode == "meta" else ("//" if mode == "hybrid" else ("\\\\" if mode == "bm25" else ".."))
        bars = ax.bar(x + (i - n / 2 + 0.5) * width, scores, width * 0.92,
                      label="META-RAG (ours)" if mode == "meta" else mode,
                      color=color, edgecolor="white", linewidth=0.5, hatch=hatch)
        for bar, s in zip(bars, scores):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015,
                    f"{s:.2f}", ha="center", va="bottom", fontsize=6.5, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels(["Known-item", "Topical", "Bibliographic fact"])
    ax.set_ylabel("nDCG@10")
    ax.set_ylim(0, 1.12)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=4, fontsize=7)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    fig.savefig(ROOT / "figures" / "fig_pertype.pdf")
    fig.savefig(ROOT / "figures" / "fig_pertype.png", dpi=300)
    print("saved figures/fig_pertype.pdf + .png")

    # ---------------- Figure 3: robustness degradation curves ----------------
    rates = sorted(noise["topical"])
    key_map = {"topical": "topical", "overall": "overall", "known": "known_item", "bib": "bib_fact"}
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for src, key in key_map.items():
        vals = [noise[src][r] for r in rates]
        ax.plot(rates, vals, label=LABELS[key], color=COLORS[key],
                marker=MARKERS[key], markersize=4, lw=1.8, zorder=3)
    ax.set_xlabel("Metadata corruption rate")
    ax.set_ylabel("nDCG@10")
    ax.set_xticks(rates)
    ax.set_xticklabels([f"{r:.0%}" for r in rates])
    ax.set_ylim(0.1, 1.02)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=4, fontsize=7)
    fig.savefig(ROOT / "figures" / "fig_robustness.pdf")
    fig.savefig(ROOT / "figures" / "fig_robustness.png", dpi=300)
    print("saved figures/fig_robustness.pdf + .png")

    print(f"\nUsed: table1 rows={list(rows)}; noise rates={rates}; "
          f"title-only topical ref={title_topical}; pvals={ {t: round(pvals[t],4) for t in TYPES} }")

    # ---------------- new-experiment figures ----------------
    fig_sparsity(p, ROOT / "figures")
    fig_loop(p, ROOT / "figures")


if __name__ == "__main__":
    main()
