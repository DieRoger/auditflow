"""Generate Audit Evidence Chain demo image (README GIF core).

One transaction's full audit trail:
  Transaction → Signals → Assessment → Review → Procedure → Evidence → Reviewer
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

IMG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "images", "evidence_chain.png")


def draw():
    # (label, color, detail)
    stages = [
        ("Transaction #T0026", "#1e293b", "Revenue recognized 2024-12-31\nAmount: $230,000"),
        ("Signals (3)", "#7c3aed", "amount_spike · weekend\nrelated_party"),
        ("Assessment", "#d97706", "overall_risk = MEDIUM\n(Evidence dominates narrative)"),
        ("Review Queue (HITL)", "#2563eb", "NEED_MORE_EVIDENCE\nRequest delivery notes"),
        ("Procedure", "#0f766e", "Revenue Cutoff Test\nSampling: ALL"),
        ("Evidence", "#16a34a", "Invoice: PRESENT\nDelivery: MISSING"),
        ("Reviewer", "#334155", "Decision: Pending"),
    ]

    fig, ax = plt.subplots(figsize=(7, 9))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, len(stages) + 1)
    ax.axis("off")

    for i, (label, color, detail) in enumerate(stages):
        y = len(stages) - i  # top to bottom
        box = FancyBboxPatch((1.5, y - 0.78), 7, 0.78,
                             boxstyle="round,pad=0.02", linewidth=0,
                             facecolor=color, alpha=0.12)
        ax.add_patch(box)
        ax.plot([1.5, 8.5], [y - 0.78, y - 0.78], color=color, lw=2, alpha=0.5)
        ax.text(5, y - 0.28, label, ha="center", va="center",
                fontsize=13, fontweight="bold", color=color)
        ax.text(5, y - 0.55, detail, ha="center", va="center",
                fontsize=9, color="#475569")

        # arrow to next stage
        if i < len(stages) - 1:
            ax.annotate("", xy=(5, y - 1.0), xytext=(5, y - 0.85),
                        arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=1.5))

    ax.set_title("Audit Evidence Chain — Transaction #T0026\n"
                 "(cutoff exception: recognized Dec 31, shipped Jan 2)",
                 fontsize=13, fontweight="bold", pad=16, color="#1e293b")
    fig.tight_layout()
    os.makedirs(os.path.dirname(IMG_PATH), exist_ok=True)
    fig.savefig(IMG_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {IMG_PATH}")


if __name__ == "__main__":
    draw()
