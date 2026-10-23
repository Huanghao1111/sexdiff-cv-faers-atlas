# -*- coding: utf-8 -*-
"""Figure 4: dictionary audit design and results (EHJ-CVP submission-grade).

Same export contract as make_figures.py: PDF (fonttype 42) + SVG + 600-dpi TIFF
+ preview PNG into ../figures/; panel alignment audited via nature-figure skill.
All numbers from compute_audit_metrics.py output (v3, gold standard locked
211/211 after arbitration of sample 492 via manufacturer label ATC C09DX01).
v3: arbitration resolved — panels a/b/c updated to final numbers; v2 had fixed
panel-a box text overflow, panel-b label placement, panel-c collisions.
"""
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Optional internal QC gate (multi-panel alignment audit used during figure
# production). Not required to reproduce the figures; skipped if unavailable.
try:
    from audit_panel_alignment import require_matplotlib_panel_alignment
except ImportError:
    def require_matplotlib_panel_alignment(*args, **kwargs):
        return None

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.normpath(os.path.join(HERE, "..", "figures"))
os.makedirs(FIGDIR, exist_ok=True)

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "font.size": 7,
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 0.8,
    "legend.frameon": False,
})

MM = 1 / 25.4
DICT_C, LLM_C, GREY = "#8C8C8C", "#2166AC", "#BFBFBF"


def save_pub(fig, name):
    require_matplotlib_panel_alignment(
        fig, json_out=os.path.join(FIGDIR, f"{name}.alignment.json"),
        overlay_svg=os.path.join(FIGDIR, f"{name}.alignment.svg"),
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(FIGDIR, f"{name}.{ext}"), bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}_preview.png"), dpi=200,
                bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


def figure4():
    fig = plt.figure(figsize=(180 * MM, 165 * MM))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 1.0], hspace=0.42,
                          wspace=0.52, left=0.055, right=0.975, top=0.95,
                          bottom=0.115)

    # ---------------- (a) audit flow ----------------
    axa = fig.add_subplot(gs[0, :])
    axa.set_xlim(0, 10); axa.set_ylim(0, 7.8); axa.axis("off")

    def box(x, y, w, h, lines, fs=6.2):
        axa.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.10",
                                     fc="white", ec="black", lw=0.8))
        for i, ln in enumerate(lines):
            axa.text(x + w / 2, y + h - 0.33 - i * 0.34, ln, ha="center",
                     va="center", fontsize=fs,
                     fontweight="bold" if i == 0 else "normal")

    def arrow(x1, y1, x2, y2):
        axa.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                      mutation_scale=8, lw=0.9, color="black"))

    box(2.7, 6.45, 4.6, 1.15, ["Stratified audit sample, seed 20261016",
                               "1,000 pairs (500 hit / 200 long-tail / 300 unmatched)",
                               "PPS-weighted; covers 9,225,001 reports"])
    box(0.30, 4.45, 4.4, 1.15, ["LLM second reader",
                                "frozen 39-class prompt, blind to dictionary",
                                "labels SHA-256 locked before key unsealed"])
    box(5.30, 4.45, 4.4, 1.15, ["Deterministic dictionary v2",
                                "labels sealed until LLM hash-lock",
                                "opened only after lock recorded"])
    box(2.9, 3.10, 4.2, 0.80, ["Comparison of label sets",
                               "986/1,000 exact match; 14 disagreements"])
    box(0.30, 1.30, 4.6, 1.15, ["Dual-blind human gold standard",
                                "14 disagreements + 197 concordant pairs",
                                "agreement 210/211; arbitration resolved 1"])
    box(5.30, 1.30, 4.4, 1.15, ["Pre-specified metrics",
                                "accuracy (Wilson), McNemar, Cohen's \u03ba",
                                "error-mode taxonomy; C-layer extrapolation"])

    arrow(4.6, 6.43, 2.7, 5.62)
    arrow(5.4, 6.43, 7.3, 5.62)
    arrow(2.7, 4.43, 4.4, 3.92)
    arrow(7.3, 4.43, 5.6, 3.92)
    arrow(4.4, 3.08, 2.8, 2.47)
    arrow(5.6, 3.08, 7.3, 2.47)
    arrow(4.92, 1.88, 5.28, 1.88)
    axa.annotate("a", xy=(0, 1.0), xycoords="axes fraction",
                 xytext=(-14, 2), textcoords="offset points",
                 fontsize=9, fontweight="bold", va="top", ha="left")

    # ---------------- (b) accuracy vs gold ----------------
    axb = fig.add_subplot(gs[1, 0])
    est = [("Dictionary", 0.953, 0.915, 0.974, DICT_C),
           ("LLM second reader", 0.981, 0.952, 0.993, LLM_C)]
    ys = [0.9, 0.0]
    for (lab, p, lo, hi, c), y in zip(est, ys):
        axb.errorbar(p, y, xerr=[[p - lo], [hi - p]], fmt="o", ms=4.5,
                     color=c, ecolor=c, elinewidth=1.2, capsize=3, zorder=3)
        axb.text(0.856, y + 0.24, f"{lab}:  {p*100:.1f}% [{lo*100:.1f}\u2013{hi*100:.1f}]",
                 fontsize=6.4, ha="left", va="bottom")
    axb.set_yticks([])
    axb.set_xlim(0.85, 1.045)
    axb.set_ylim(-0.75, 1.65)
    axb.set_xticks([0.85, 0.90, 0.95, 1.00])
    axb.set_xticklabels(["85", "90", "95", "100"])
    axb.set_xlabel("Pair-level exact-match accuracy vs gold standard, % (n = 211)",
                   fontsize=6.4)
    axb.axvline(1.0, color=GREY, lw=0.7, ls=":", zorder=1)
    axb.text(0.856, -0.62, "Exact McNemar p = 0.180; inter-rater agreement 210/211 (99.5%)",
             fontsize=5.9, color="#404040")
    axb.annotate("b", xy=(0, 1.0), xycoords="axes fraction",
                 xytext=(-14, 2), textcoords="offset points",
                 fontsize=9, fontweight="bold", va="top", ha="left")

    # ---------------- (c) error modes ----------------
    axc = fig.add_subplot(gs[1, 1])
    cats = ["scope_dispute (PDE5/PAH)",
            "scope_dispute (tirzepatide)",
            "combination_partial",
            "missed_brand",
            "missed_ingredient"]
    d_vals = [4, 0, 3, 2, 1]
    l_vals = [0, 4, 0, 0, 0]
    ypos = list(range(len(cats)))[::-1]
    h = 0.36
    axc.barh([y + h/2 for y in ypos], d_vals, height=h, color=DICT_C,
             label="Dictionary", zorder=3)
    axc.barh([y - h/2 for y in ypos], l_vals, height=h, color=LLM_C,
             label="LLM second reader", zorder=3)
    for y, v in zip(ypos, d_vals):
        if v:
            axc.text(v + 0.06, y + h/2, str(v), va="center", fontsize=6.2)
    for y, v in zip(ypos, l_vals):
        if v:
            axc.text(v + 0.06, y - h/2, str(v), va="center", fontsize=6.2)
    axc.set_yticks(ypos)
    axc.set_yticklabels(cats, fontsize=6.0)
    axc.set_xlim(0, 5.4)
    axc.set_xticks([0, 1, 2, 3, 4, 5])
    axc.set_xlabel("Pairs with error (n = 211)", fontsize=6.4)
    axc.legend(fontsize=6.2, loc="center right")
    axc.text(0.0, -0.34, "All 211 gold-standard pairs final (sample 492 resolved via manufacturer\n"
                         "label, ATC C09DX01); error modes with zero observed pairs not shown.",
             transform=axc.transAxes, fontsize=5.9, color="#404040", va="top")
    axc.text(-0.38, 1.10, "c", fontsize=9, fontweight="bold", va="top",
             transform=axc.transAxes)

    save_pub(fig, "figure4_audit")


if __name__ == "__main__":
    figure4()
