"""Deck-only figures.

The 5-panel SHAP figure (fig11) is right for the repository — all five classes side by side —
but at slide scale its type falls below ~5 pt and feature names truncate. So the deck gets a
purpose-built 2-panel version showing only the two families the slide actually argues about
(R2L and U2R), with full feature names at readable size.

Writes reports/figures/fig12_shap_r2l_u2r_deck.png
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import FIGURES, METRICS
from plots import GRID, INK, INK2, MUTED, SURFACE, YELLOW, MAGENTA, _save

plt.rcParams.update({
    "font.family": ["DejaVu Sans"], "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": "#c3c2b7", "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.9,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.dpi": 110,
})

PRETTY = {
    "dst_host_same_src_port_rate": "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate": "dst_host_srv_diff_host_rate",
}


def main():
    d = json.loads((METRICS / "explainability.json").read_text())
    top = d["shap_top8_per_family"]
    fams = [("R2L", YELLOW, "R2L — remote-to-local intrusion"),
            ("U2R", MAGENTA, "U2R — privilege escalation")]
    fams = [f for f in fams if f[0] in top]

    fig, axes = plt.subplots(1, len(fams), figsize=(13.0, 4.15))
    if len(fams) == 1:
        axes = [axes]

    content = {"root_shell", "hot", "num_file_creations", "is_guest_login", "logged_in",
               "num_failed_logins", "num_shells", "num_root", "su_attempted",
               "num_compromised", "num_access_files"}

    for ax, (f, col, title) in zip(axes, fams):
        dd = top[f][::-1]
        vals = [e["mean_abs_shap"] for e in dd]
        names = [PRETTY.get(e["feature"], e["feature"]) for e in dd]
        base = [n.split("__")[0] for n in names]
        cols = ["#0ca30c" if b in content else col for b in base]
        y = np.arange(len(names))
        ax.barh(y, vals, height=0.62, color=cols, zorder=3)
        for yi, v in zip(y, vals):
            ax.text(v + max(vals) * 0.02, yi, f"{v:.4f}", va="center",
                    color=INK, fontsize=11)
        ax.set_yticks(y, names, color=INK, fontsize=13)
        ax.set_title(title, loc="left", fontweight="bold", color=INK, fontsize=15, pad=12)
        ax.set_axisbelow(True)
        ax.grid(axis="x"); ax.grid(axis="y", visible=False)
        ax.tick_params(length=0)
        ax.set_xlabel("mean |SHAP| — contribution to this verdict", fontsize=12, labelpad=8)
        ax.set_xlim(0, max(vals) * 1.30)
        ax.set_ylim(-0.7, len(names) - 0.3)
        # Cap tick count — the default locator crowds these small magnitudes into
        # unreadable, touching labels.
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4, prune=None))
        ax.tick_params(axis="x", labelsize=11)

    # Legend explaining the green highlight, placed in figure space (no axes collision).
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor="#0ca30c", label="content (payload-derived) feature — "
                                                        "only 1.2% of total model importance")],
               loc="lower left", bbox_to_anchor=(0.005, -0.02), fontsize=12)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _save(fig, "fig12_shap_r2l_u2r_deck")


if __name__ == "__main__":
    main()
