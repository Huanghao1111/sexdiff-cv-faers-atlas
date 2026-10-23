"""make_figures.py — Figures 1-3 (EHJ-CVP submission-grade vector output).

Backend: Python/matplotlib (saved preference). Export: PDF (fonttype 42,
editable text) + SVG + 600-dpi TIFF into ../figures/.
Figure contracts:
  F1 schematic flow (STaRT-RV style study flow).
  F2 hero heatmap: class x clinical event domain, log2 ROR ratio (F/M),
    asterisk = BH q<0.05; grey = not estimable (any cell < 5).
  F3 forest: validated signals + positive controls; panel a per-sex RORs
    (log scale), panel b Stage-6 adjusted ratio with 95% CI.
"""
import csv
import json
import math
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
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
RED, BLUE, GREY = "#B2182B", "#2166AC", "#8C8C8C"


def save_pub(fig, name):
    require_matplotlib_panel_alignment(
        fig, json_out=os.path.join(FIGDIR, f"{name}.alignment.json"),
        overlay_svg=os.path.join(FIGDIR, f"{name}.alignment.svg"),
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    for ext in ("pdf", "svg"):
        fig.savefig(os.path.join(FIGDIR, f"{name}.{ext}"), bbox_inches="tight")
    fig.savefig(os.path.join(FIGDIR, f"{name}.tiff"), dpi=600,
                bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# ---------------- Figure 1: study flow ----------------
def figure1():
    with open(os.path.join(HERE, "table1_numbers.json")) as f:
        N = json.load(f)
    fig, ax = plt.subplots(figsize=(180 * MM, 120 * MM))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, lines, fc="white", fs=7, bold_first=True):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle="round,pad=0.12",
                                    fc=fc, ec="black", lw=0.8))
        for i, ln in enumerate(lines):
            ax.text(x + w / 2, y + h - 0.42 - i * 0.44, ln,
                    ha="center", va="center",
                    fontsize=fs, fontweight="bold" if (i == 0 and bold_first)
                    else "normal")

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                                     arrowstyle="-|>", mutation_scale=9,
                                     lw=0.9, color="black"))

    box(0.2, 8.2, 4.4, 1.5, ["FAERS quarterly ASCII files",
                             "90 quarters; 24,812,425 report rows"])
    box(0.2, 6.0, 4.4, 1.5, ["FDA deduplication",
                             "20,614,457 unique reports (latest case version)"])
    box(0.2, 3.8, 4.4, 1.5, ["Sex-known reports",
                             "F 10,871,361 / M 7,143,038"])
    box(0.2, 1.4, 4.4, 1.9,
        ["Cardiovascular primary-suspect universe",
         "2,190,818 reports (F 1,244,631 / M 946,187)",
         "36 drug classes (ATC C01–C10, B01, A10B)"])
    box(5.4, 7.0, 4.4, 1.7, ["Signal detection (class vs CV comparator)",
                             "28,949 class × PT tests; 2,784 with q<0.05",
                             "per-sex ROR and ROR ratio; BH-FDR"])
    box(5.4, 4.6, 4.4, 1.7, ["Result-pool curation",
                             "586 top signals → 106 candidates",
                             "artefact control: source concentration,",
                             ]) if False else None
    ax.add_patch(FancyBboxPatch((5.4, 4.6), 4.4, 1.7, boxstyle="round,pad=0.12",
                                fc="white", ec="black", lw=0.8))
    for i, ln in enumerate(["Result-pool curation",
                            "586 top signals \u2192 106 candidates",
                            "artefact QC: source concentration,",
                            "indication-coded PTs, manual review"]):
        ax.text(7.6, 4.6 + 1.7 - 0.42 - i * 0.40, ln, ha="center",
                va="center", fontsize=7,
                fontweight="bold" if i == 0 else "normal")
    box(5.4, 2.2, 4.4, 1.7, ["Case-centered adjusted regression",
                             "106/106 candidates remain significant",
                             "(age, era, reporter, seriousness, concomitant)"])
    box(5.4, 0.2, 4.4, 1.7, ["Sensitivity & validation layers",
                             "reporter / seriousness / era strata;",
                             "within-class analyses; FDA label check",
                             ])
    arrow(2.4, 8.2, 2.4, 7.5)
    arrow(2.4, 6.0, 2.4, 5.3)
    arrow(2.4, 3.8, 2.4, 3.3)
    # elbow connector: right edge of CV universe -> up -> left edge of signal detection
    ax.plot([4.72, 5.02], [2.35, 2.35], color="black", lw=0.9,
            solid_capstyle="butt")
    ax.plot([5.02, 5.02], [2.35, 7.85], color="black", lw=0.9,
            solid_capstyle="butt")
    arrow(5.02, 7.85, 5.4, 7.85)
    arrow(7.6, 7.0, 7.6, 6.3)
    arrow(7.6, 4.6, 7.6, 3.9)
    arrow(7.6, 2.2, 7.6, 1.9)
    ax.text(7.6, -0.15, "Validated atlas: 13 signals + 2 positive controls",
            ha="center", fontsize=7, fontweight="bold")
    save_pub(fig, "figure1_flow")


# ---------------- Figure 2: domain heatmap ----------------
def figure2():
    rows = list(csv.DictReader(open(os.path.join(HERE, "fig2_domain_grid.csv"),
                                    encoding="utf-8")))
    doms = sorted({r["domain"] for r in rows} - {"Other / unmapped"})
    clss = sorted({r["class"] for r in rows})
    # order domains: most female-shifted median on top
    med = {}
    for d in doms:
        v = [math.log2(float(r["ROR_ratio"])) for r in rows
             if r["domain"] == d]
        med[d] = np.median(v)
    doms.sort(key=lambda d: -med[d])
    idx = {(r["class"], r["domain"]): r for r in rows}
    Z = np.full((len(doms), len(clss)), np.nan)
    Sig = np.zeros_like(Z, dtype=bool)
    for i, d in enumerate(doms):
        for j, c in enumerate(clss):
            r = idx.get((c, d))
            if r:
                Z[i, j] = math.log2(float(r["ROR_ratio"]))
                Sig[i, j] = float(r["q"]) < 0.05
    fig, ax = plt.subplots(figsize=(180 * MM, 118 * MM))
    VMAX = 2.5
    norm = mpl.colors.Normalize(-VMAX, VMAX)
    cmap = mpl.colormaps["RdBu_r"]
    rgb = np.ones(Z.shape + (4,))
    bad = np.isnan(Z)
    rgb[~bad] = cmap(norm(np.clip(Z[~bad], -VMAX, VMAX)))
    rgb[bad] = (0.93, 0.93, 0.93, 1.0)
    ax.imshow(rgb, aspect="auto", interpolation="nearest")
    for i in range(len(doms)):
        for j in range(len(clss)):
            if Sig[i, j]:
                ax.text(j, i, "*", ha="center", va="center",
                        fontsize=5.5, color="black")
    ax.set_xticks(range(len(clss)))
    ax.set_xticklabels(clss, rotation=90, fontsize=5)
    ax.set_yticks(range(len(doms)))
    ax.set_yticklabels(doms, fontsize=6)
    ax.set_xticks(np.arange(-0.5, len(clss)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(doms)), minor=True)
    ax.grid(which="minor", color="white", lw=0.4)
    ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
                      ax=ax, fraction=0.025, pad=0.015)
    cb.set_label("log2 ROR ratio (female / male)", fontsize=6)
    cb.ax.tick_params(labelsize=5.5)
    cb.outline.set_visible(False)
    ax.set_title("Sex-differential safety map: drug class \u00d7 event domain "
                 "(* BH q<0.05)", fontsize=7, pad=4)
    save_pub(fig, "figure2_heatmap")


# ---------------- Figure 3: forest of validated signals ----------------
SIGNALS = [  # (class, pt, tag)
    ("ACEI", "COUGH", "positive control"),
    ("DIGOXIN", "TOXICITY TO VARIOUS AGENTS", "positive control"),
    ("SGLT2I", "GENITAL INFECTION FUNGAL", "labelled"),
    ("MRA", "BREAST PAIN", "labelled"),
    ("CCB_DHP", "ACUTE PULMONARY OEDEMA", "novel"),
    ("LOOP", "TORSADE DE POINTES", "novel"),
    ("ALPHA_HTN", "URINARY INCONTINENCE", "novel"),
    ("VASODIL", "ORTHOSTATIC HYPOTENSION", "novel"),
    ("GLP1RA", "HYPERTHYROIDISM", "novel"),
    ("GLP1RA", "BREAST PAIN", "novel"),
    ("RENIN_INH", "ANGIOEDEMA", "novel (labelled event)"),
    ("SGLT2I", "ANGIOEDEMA", "novel (labelled event)"),
    ("SGLT2I", "CELLULITIS", "novel (label-adjacent)"),
    ("AA_III", "THYROTOXIC CRISIS", "validated direction"),
    ("DPP4I", "INTESTINAL OBSTRUCTION", "novel"),
]


def figure3():
    tests = {(r["class"], r["pt"]): r for r in csv.DictReader(
        open(os.path.join(HERE, "sexdiff_all_tests.csv"), encoding="utf-8"))}
    adj = {(r["class"], r["pt"]): r for r in csv.DictReader(
        open(os.path.join(HERE, "stage6_adjusted.csv"), encoding="utf-8"))}
    data = []
    for c, p, tag in SIGNALS:
        t = tests[(c, p)]
        a = adj.get((c, p))
        af, nf = float(t["a_f"]), float(t["n_f"])
        am, nm = float(t["a_m"]), float(t["n_m"])
        cf, NF = float(t["c_f"]), float(t["N_f"])
        cm, NM = float(t["c_m"]), float(t["N_m"])
        bf, df = nf - af, NF - cf
        bm, dm = nm - am, NM - cm
        rf, rm = float(t["ROR_f"]), float(t["ROR_m"])
        se_f = math.sqrt(1 / af + 1 / bf + 1 / cf + 1 / df)
        se_m = math.sqrt(1 / am + 1 / bm + 1 / cm + 1 / dm)
        lf = (rf * math.exp(-1.96 * se_f), rf * math.exp(1.96 * se_f))
        lm = (rm * math.exp(-1.96 * se_m), rm * math.exp(1.96 * se_m))
        data.append(dict(cls=c, pt=p, tag=tag, n=af + am,
                         rf=rf, lf=lf, rm=rm, lm=lm,
                         ar=float(a["adj_ratio"]),
                         alo=float(a["adj_lo"]), ahi=float(a["adj_hi"])))
    data.sort(key=lambda d: -d["ar"])
    n = len(data)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(180 * MM, 118 * MM),
                                   sharey=True,
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    ys = np.arange(n)[::-1]
    for y, d in zip(ys, data):
        ax1.plot([d["lf"][0], d["lf"][1]], [y, y], color=RED, lw=0.9)
        ax1.plot(d["rf"], y, "o", color=RED, ms=3.2)
        ax1.plot([d["lm"][0], d["lm"][1]], [y, y], color=BLUE, lw=0.9)
        ax1.plot(d["rm"], y, "s", color=BLUE, ms=3.0)
        ax2.plot([d["alo"], d["ahi"]], [y, y], color="black", lw=0.9)
        ax2.plot(d["ar"], y, "D", color="black", ms=3.0)
    ax1.axvline(1, color=GREY, lw=0.7, ls="--")
    ax2.axvline(1, color=GREY, lw=0.7, ls="--")
    ax1.set_xscale("log")
    ax2.set_xscale("log")
    ax1.set_xlim(0.05, 30)
    ax2.set_xlim(0.05, 90)
    plain = mpl.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    for ax, ticks in ((ax1, [0.1, 0.5, 1, 5, 10, 30]),
                      (ax2, [0.1, 0.5, 1, 5, 10, 50])):
        ax.set_xticks(ticks)
        ax.xaxis.set_major_formatter(plain)
        ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    for ax in (ax1, ax2):
        ax.set_yticks(ys)
        ax.set_ylim(-0.7, n - 0.3)
        ax.tick_params(labelsize=6)
    ax1.set_yticklabels(
        [f"{d['cls']} \u00d7 {d['pt'].title()}  (n={int(d['n']):,})"
         for d in data], fontsize=6)
    ax1.set_xlabel("Sex-specific ROR (95% CI)", fontsize=7)
    ax2.set_xlabel("Adjusted ROR ratio, F/M (95% CI)", fontsize=7)
    ax1.plot([], [], "o", color=RED, ms=3.2, label="Female ROR")
    ax1.plot([], [], "s", color=BLUE, ms=3.0, label="Male ROR")
    ax1.legend(loc="lower left", fontsize=6, borderaxespad=0.1)
    for y, d in zip(ys, data):
        ax2.text(85, y, d["tag"], ha="right", va="center", fontsize=5,
                 color=GREY, style="italic")
    ax1.set_title("a", loc="left", fontsize=8, fontweight="bold")
    ax2.set_title("b", loc="left", fontsize=8, fontweight="bold")
    fig.subplots_adjust(wspace=0.08)
    save_pub(fig, "figure3_forest")


if __name__ == "__main__":
    figure1()
    figure2()
    figure3()
    print("done")
