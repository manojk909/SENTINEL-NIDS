"""Figure generation for SENTINEL-NIDS.

Palette is the validated reference instance (adjacent + all-pairs CVD-safe on the light
surface; verified with the palette validator). Aqua sits below 3:1 contrast on the light
surface, so the relief rule applies: every categorical mark carries a direct value label.

Rules applied throughout: one axis per chart, recessive grid, thin marks, legend whenever
>= 2 series, direct labels rather than a number on every gridline, no dual-axis, no rainbow.

Writes PNG (300 dpi, for the deck) + SVG to reports/figures/.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from config import FAMILIES, FIGURES, METRICS

# ---- validated palette (light surface) ----
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
CRITICAL, GOOD, WARNING = "#d03b3b", "#0ca30c", "#fab219"
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#dcdbd3", "#c3c2b7"
# sequential blue ramp, steps 100 -> 700
BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
             "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
SEQ = LinearSegmentedColormap.from_list("seqblue", BLUE_RAMP)

plt.rcParams.update({
    "font.family": ["DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "axes.edgecolor": BASELINE,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.9,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 11, "axes.titlesize": 13, "legend.frameon": False,
    "lines.linewidth": 2, "figure.dpi": 110,
})


def _clean(ax, ygrid=True):
    ax.set_axisbelow(True)
    ax.grid(axis="y" if ygrid else "x")
    ax.grid(axis="x" if ygrid else "y", visible=False)
    ax.tick_params(length=0)


def _save(fig, name):
    for ext in ("png", "svg"):
        fig.savefig(FIGURES / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[fig] {name}.png")


def load():
    lk = json.loads((METRICS / "leakage_experiment.json").read_text())
    ds = json.loads((METRICS.parent.parent / "data" / "processed"
                     / "dataset_summary.json").read_text())
    mc_p = METRICS / "model_comparison.json"
    zd_p = METRICS / "zeroday_experiment.json"
    mc = json.loads(mc_p.read_text()) if mc_p.exists() else None
    zd = json.loads(zd_p.read_text()) if zd_p.exists() else None
    return lk, ds, mc, zd


# ------------------------------------------------------------------ fig 1
def fig_leakage_gap(lk):
    """The headline. Same model, same features — only the evaluation protocol differs."""
    A, B = lk["protocol_A_pooled_random_split"], lk["protocol_B_official_split"]
    metrics = ["accuracy", "macro_f1", "balanced_accuracy"]
    names = ["Accuracy", "Macro-F1", "Balanced accuracy"]
    a = [A[m] for m in metrics]
    b = [B[m] for m in metrics]

    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    y = np.arange(len(metrics))
    h, gap = 0.24, 0.03

    ax.barh(y + (h + gap) / 2, a, height=h, color=BLUE, zorder=3,
            label="Protocol A — pooled random split  (the common error)")
    ax.barh(y - (h + gap) / 2, b, height=h, color=ORANGE, zorder=3,
            label="Protocol B — official KDDTrain+ → KDDTest+  (honest)")

    for yi, v in zip(y + (h + gap) / 2, a):
        ax.text(v + 0.012, yi, f"{v:.3f}", va="center", ha="left",
                color=INK, fontsize=11, fontweight="bold")
    for yi, v in zip(y - (h + gap) / 2, b):
        ax.text(v + 0.012, yi, f"{v:.3f}", va="center", ha="left",
                color=INK, fontsize=11, fontweight="bold")

    ax.set_yticks(y, names, color=INK, fontsize=11)
    ax.set_xlim(0, 1.18)
    ax.set_ylim(-0.55, len(metrics) - 0.45)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0", "0.25", "0.50", "0.75", "1.0"])
    _clean(ax, ygrid=False)
    ax.set_title("Identical model. Identical features. Only the split differs.",
                 loc="left", fontweight="bold", pad=28)
    ax.text(0, 1.06, "RandomForest(300) on NSL-KDD · 5-class attack-family task",
            transform=ax.transAxes, color=MUTED, fontsize=10)
    ax.set_xlabel("Score", labelpad=8)
    # Legend below the axes — cannot collide with value labels or the subtitle.
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.16), fontsize=9.5,
              ncol=1, handlelength=1.4, handleheight=0.9)
    _save(fig, "fig1_leakage_gap")


# ------------------------------------------------------------------ fig 2
def fig_per_class_recall(lk):
    """Where the collapse actually happens — the two rarest, most severe families."""
    A, B = lk["protocol_A_pooled_random_split"], lk["protocol_B_official_split"]
    a = [A["per_class_recall"][c] for c in FAMILIES]
    b = [B["per_class_recall"][c] for c in FAMILIES]
    sup = [B["per_class_support"][c] for c in FAMILIES]

    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    x = np.arange(len(FAMILIES))
    w, gap = 0.34, 0.03
    ax.bar(x - (w + gap) / 2, a, width=w, color=BLUE, zorder=3,
           label="Protocol A — pooled random split")
    ax.bar(x + (w + gap) / 2, b, width=w, color=ORANGE, zorder=3,
           label="Protocol B — official split (honest)")

    for xi, v in zip(x - (w + gap) / 2, a):
        ax.text(xi, v + 0.022, f"{v:.2f}", ha="center", color=INK, fontsize=10)
    for xi, v in zip(x + (w + gap) / 2, b):
        col = CRITICAL if v < 0.10 else INK
        wt = "bold" if v < 0.10 else "normal"
        ax.text(xi, v + 0.022, f"{v:.3f}", ha="center", color=col,
                fontsize=10, fontweight=wt)

    ax.set_xticks(x, [f"{c}\n{s:,} in test" for c, s in zip(FAMILIES, sup)],
                  color=INK, fontsize=10.5)
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("Recall")
    _clean(ax)
    ax.set_title("The collapse is concentrated in the two rarest — and most severe — families",
                 loc="left", fontweight="bold", pad=30)
    ax.text(0, 1.055,
            "R2L = remote-to-local intrusion · U2R = privilege escalation. "
            "Both signify actual compromise, not mere disruption.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    ax.legend(loc="upper right", fontsize=9.5, bbox_to_anchor=(1.0, 0.99))
    _save(fig, "fig2_per_class_recall")


# ------------------------------------------------------------------ fig 3
def fig_prior_shift(ds):
    """Why it collapses: the class priors themselves move between train and test."""
    tr, te = ds["family_counts_train"], ds["family_counts_test"]
    ntr, nte = sum(tr.values()), sum(te.values())
    a = [100 * tr.get(c, 0) / ntr for c in FAMILIES]
    b = [100 * te.get(c, 0) / nte for c in FAMILIES]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    x = np.arange(len(FAMILIES))
    w, gap = 0.34, 0.03
    ax.bar(x - (w + gap) / 2, a, width=w, color=BLUE, zorder=3, label="KDDTrain+ (125,973)")
    ax.bar(x + (w + gap) / 2, b, width=w, color=ORANGE, zorder=3, label="KDDTest+ (22,544)")

    for xi, v in zip(x - (w + gap) / 2, a):
        ax.text(xi, v + 0.9, f"{v:.2f}%", ha="center", color=INK, fontsize=9.5)
    for xi, v in zip(x + (w + gap) / 2, b):
        ax.text(xi, v + 0.9, f"{v:.2f}%", ha="center", color=INK, fontsize=9.5)

    for i in range(len(FAMILIES)):
        if a[i] > 0 and b[i] / a[i] > 3:
            ax.annotate(f"×{b[i]/a[i]:.0f}", xy=(i, max(a[i], b[i]) + 5.4),
                        ha="center", color=CRITICAL, fontweight="bold", fontsize=12)

    ax.set_xticks(x, FAMILIES, color=INK, fontsize=11)
    ax.set_ylabel("Share of split (%)")
    ax.set_ylim(0, 62)
    _clean(ax)
    ax.set_title("The class priors move — the test set is not the training distribution",
                 loc="left", fontweight="bold", pad=30)
    ax.text(0, 1.055,
            "R2L rises 15× and U2R 21× from train to test. This shift is by design in "
            "NSL-KDD, and pooling the splits destroys it.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    ax.legend(loc="upper right", fontsize=9.5, bbox_to_anchor=(1.0, 0.99))
    _save(fig, "fig3_class_prior_shift")


# ------------------------------------------------------------------ fig 4
def fig_novel_vs_seen(lk):
    """A single comparison that states the operational consequence."""
    fa = lk["failure_analysis"]
    seen = fa["seen_attacks"]["missed_as_normal_rate"]
    novel = fa["novel_attacks"]["missed_as_normal_rate"]

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    bars = ["Attack types seen\nduring training", "Attack types NEVER seen\nduring training"]
    vals, cols = [seen, novel], [WARNING, CRITICAL]
    ns = [fa["seen_attacks"]["n"], fa["novel_attacks"]["n"]]

    b = ax.barh([1, 0], vals, height=0.30, color=cols, zorder=3)
    for rect, v, n in zip(b, vals, ns):
        ax.text(v + 0.015, rect.get_y() + rect.get_height() / 2,
                f"{v*100:.1f}%   ({n:,} flows)", va="center", color=INK,
                fontsize=12, fontweight="bold")

    ax.set_yticks([1, 0], bars, color=INK, fontsize=11)
    # Headroom so the direct value label never touches the panel edge.
    ax.set_xlim(0, 1.22)
    ax.set_ylim(-0.6, 1.6)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    _clean(ax, ygrid=False)
    ax.set_xlabel("Share of attacks silently labelled “normal”")
    ax.set_title("What the 99.5% model does with an attack it has never seen",
                 loc="left", fontweight="bold", pad=34)
    ax.text(0, 1.10,
            "Missing an attack is not a wrong label — it is an intrusion that raises no "
            "alarm at all.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    _save(fig, "fig4_novel_vs_seen")


# ------------------------------------------------------------------ fig 5
def fig_model_comparison(mc):
    """Comparative analysis. Sorted by the metric of record, not by accuracy."""
    if not mc:
        print("[fig] skipping fig5 — model_comparison.json not present yet")
        return
    ok = {k: v for k, v in mc["models"].items() if "macro_f1" in v}
    items = sorted(ok.items(), key=lambda kv: kv[1]["macro_f1"])
    labels = [k.split("_", 1)[1].replace("_", " ") for k, _ in items]
    f1 = [v["macro_f1"] for _, v in items]
    cv = [v.get("cv_macro_f1_mean_on_train") for _, v in items]

    fig, ax = plt.subplots(figsize=(9.8, 5.4))
    y = np.arange(len(labels))
    h, gap = 0.26, 0.03
    ax.barh(y + (h + gap) / 2, [c if c is not None else 0 for c in cv], height=h,
            color=BLUE, zorder=3,
            label=f"{mc['cv_folds_on_train']}-fold CV macro-F1 on KDDTrain+  (in-distribution)")
    ax.barh(y - (h + gap) / 2, f1, height=h, color=ORANGE, zorder=3,
            label="Macro-F1 on official KDDTest+  (under distribution shift)")

    for yi, v in zip(y + (h + gap) / 2, cv):
        if v is not None:
            ax.text(v + 0.01, yi, f"{v:.3f}", va="center", color=INK, fontsize=9.5)
    for yi, v in zip(y - (h + gap) / 2, f1):
        ax.text(v + 0.01, yi, f"{v:.3f}", va="center", color=INK, fontsize=9.5,
                fontweight="bold")

    ax.set_yticks(y, labels, color=INK, fontsize=10.5)
    ax.set_xlim(0, 1.14)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_xlabel("Macro-F1", labelpad=8)
    _clean(ax, ygrid=False)
    ax.set_title("Every model looks excellent in-distribution. None survives the shift.",
                 loc="left", fontweight="bold", pad=28)
    ax.text(0, 1.045,
            "The ranking barely matters: the gap between the two bars dwarfs the gap "
            "between any two models.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.11), fontsize=9,
              handlelength=1.4, handleheight=0.9)
    _save(fig, "fig5_model_comparison")


# ------------------------------------------------------------------ fig 6
def fig_confusion(lk):
    """Sequential single-hue ramp, row-normalised. Never a rainbow."""
    cm = np.array(lk["protocol_B_official_split"]["confusion_matrix"], dtype=float)
    labels = lk["protocol_B_official_split"]["confusion_matrix_labels"]
    row = cm / cm.sum(axis=1, keepdims=True)

    fig, ax = plt.subplots(figsize=(6.8, 5.8))
    im = ax.imshow(row, cmap=SEQ, vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)), labels, color=INK)
    ax.set_yticks(range(len(labels)), labels, color=INK)
    ax.set_xlabel("Predicted family"); ax.set_ylabel("True family")
    ax.grid(False)
    ax.tick_params(length=0)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{row[i,j]*100:.1f}%\n{int(cm[i,j]):,}",
                    ha="center", va="center", fontsize=9,
                    color="#ffffff" if row[i, j] > 0.55 else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Share of true family", color=INK2)
    cb.outline.set_visible(False)
    ax.set_title("Honest protocol: where the traffic actually goes",
                 loc="left", fontweight="bold", pad=26)
    ax.text(0, 1.05, "Row-normalised. The left column is the operationally dangerous one.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    _save(fig, "fig6_confusion_matrix")


# ------------------------------------------------------------------ fig 7
def fig_per_novel_attack(lk):
    """Per-attack-type detection on the 17 unseen types. Honest: shows the zeros."""
    d = lk["failure_analysis"]["per_novel_attack_type"]
    items = sorted(d.items(), key=lambda kv: kv[1]["detected_as_attack_rate"])
    names = [f"{k}  ({v['n']:,})" for k, v in items]
    vals = [v["detected_as_attack_rate"] for _, v in items]
    cols = [CRITICAL if v < 0.34 else (WARNING if v < 0.67 else GOOD) for v in vals]

    fig, ax = plt.subplots(figsize=(8.8, 6.6))
    y = np.arange(len(names))
    ax.barh(y, vals, height=0.58, color=cols, zorder=3)
    for yi, v in zip(y, vals):
        ax.text(v + 0.014, yi, f"{v*100:.0f}%", va="center", color=INK, fontsize=9.5)
    ax.set_yticks(y, names, color=INK, fontsize=9.5)
    ax.set_xlim(0, 1.1)
    ax.set_ylim(-0.7, len(names) - 0.3)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    _clean(ax, ygrid=False)
    ax.set_xlabel("Detected as an attack (any family)", labelpad=8)
    ax.set_title("The 17 attack types the model was never trained on",
                 loc="left", fontweight="bold", pad=30)
    ax.text(0, 1.035,
            "Bar length is “raised any alarm at all”, not “classified correctly”. "
            "Red = under one third detected.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    _save(fig, "fig7_per_novel_attack")


# ------------------------------------------------------------------ fig 8
def fig_hybrid_curve(zd):
    """The fix: unseen-attack detection gained vs false-alarm cost paid."""
    if not zd or "hybrid" not in zd:
        print("[fig] skipping fig8 — zeroday_experiment.json not present yet")
        return
    curve = zd["hybrid"]["operating_curve"]
    far = [r["A_with_abstention_OR_B"]["false_alarm_rate"] for r in curve]
    nov = [r["A_with_abstention_OR_B"]["novel_attack_detection_rate"] for r in curve]
    taus = [r["tau"] for r in curve]
    base = zd["hybrid"]["channel_A_only_no_abstention"]

    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ax.plot(far, nov, color=BLUE, marker="o", markersize=7, zorder=3,
            label="SENTINEL hybrid — abstention + anomaly channel")
    ax.scatter([base["false_alarm_rate"]], [base["novel_attack_detection_rate"]],
               s=150, color=CRITICAL, zorder=5, marker="X",
               label="Plain 5-class classifier (baseline)")

    # Label a few operating points directly rather than every point.
    for f, n, t in zip(far, nov, taus):
        if t == 0.0:      # left of the cluster, clear of the markers
            ax.annotate(f"τ={t}", (f, n), textcoords="offset points",
                        xytext=(-10, -18), color=INK2, fontsize=9, ha="center")
        elif t in (0.99, 0.999):
            ax.annotate(f"τ={t}", (f, n), textcoords="offset points",
                        xytext=(10, -6), color=INK2, fontsize=9)
    ax.annotate("plain classifier\n(baseline)",
                (base["false_alarm_rate"], base["novel_attack_detection_rate"]),
                textcoords="offset points", xytext=(14, -6), color=CRITICAL,
                fontsize=9.5, fontweight="bold", va="center")

    rp = zd["hybrid"].get("recommended_operating_point")
    if rp:
        ax.scatter([rp["false_alarm_rate"]], [rp["novel_attack_detection_rate"]],
                   s=210, facecolor="none", edgecolor=GOOD, linewidth=2.5, zorder=6)
        # Text parked in empty canvas rather than arrowed across the curve.
        ax.text(0.30, 0.985,
                f"◯  recommended operating point:  τ={rp['tau']}\n"
                f"     {rp['novel_attack_detection_rate']*100:.0f}% unseen-attack coverage "
                f"at {rp['false_alarm_rate']*100:.1f}% false alarms\n"
                f"     (best coverage subject to a 10% false-alarm ceiling)",
                transform=ax.transAxes, color=GOOD, fontsize=9.5, fontweight="bold",
                ha="left", va="top", linespacing=1.5)

    ax.set_xlabel("False-alarm rate on normal traffic", labelpad=8)
    ax.set_ylabel("Unseen-attack detection rate")
    ax.set_ylim(0, 1.05)
    _clean(ax)
    ax.grid(axis="x")
    ax.set_title("The fix: buying unseen-attack coverage with false alarms",
                 loc="left", fontweight="bold", pad=30)
    ax.text(0, 1.05,
            "A security team picks the point on this curve. We report the whole curve "
            "rather than choosing for them.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    ax.legend(loc="lower right", fontsize=9.5)
    _save(fig, "fig8_hybrid_operating_curve")


# ------------------------------------------------------------------ fig 9
def fig_lofo(zd):
    """Leave-One-Family-Out: controlled zero-day, one family at a time."""
    if not zd or "lofo" not in zd:
        print("[fig] skipping fig9 — zeroday_experiment.json not present yet")
        return
    fams = list(zd["lofo"].keys())
    inc = [zd["lofo"][f]["detection_rate_family_INCLUDED"] for f in fams]
    held = [zd["lofo"][f]["detection_rate_family_HELD_OUT"] for f in fams]

    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    x = np.arange(len(fams))
    w, gap = 0.34, 0.03
    ax.bar(x - (w + gap) / 2, inc, width=w, color=BLUE, zorder=3,
           label="Family present in training")
    ax.bar(x + (w + gap) / 2, held, width=w, color=ORANGE, zorder=3,
           label="Family removed from training  (simulated zero-day)")
    for xi, v in zip(x - (w + gap) / 2, inc):
        ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", color=INK, fontsize=10)
    for xi, v in zip(x + (w + gap) / 2, held):
        col = CRITICAL if v < 0.5 else INK
        ax.text(xi, v + 0.02, f"{v:.2f}", ha="center", color=col, fontsize=10,
                fontweight="bold" if v < 0.5 else "normal")

    ax.set_xticks(x, fams, color=INK, fontsize=11)
    ax.set_ylabel("Detection rate on that family")
    ax.set_ylim(0, 1.15)
    _clean(ax)
    ax.set_title("Leave-One-Family-Out: what happens when an attack class is genuinely new",
                 loc="left", fontweight="bold", pad=30)
    ax.text(0, 1.05,
            "Each bar pair retrains from scratch with that family deleted from the "
            "training set, then tests on it.",
            transform=ax.transAxes, color=MUTED, fontsize=9.5)
    ax.legend(loc="lower left", fontsize=9.5)
    _save(fig, "fig9_lofo")


if __name__ == "__main__":
    lk, ds, mc, zd = load()
    fig_leakage_gap(lk)
    fig_per_class_recall(lk)
    fig_prior_shift(ds)
    fig_novel_vs_seen(lk)
    fig_confusion(lk)
    fig_per_novel_attack(lk)
    fig_model_comparison(mc)
    fig_hybrid_curve(zd)
    fig_lofo(zd)
    print("[fig] done ->", FIGURES)
