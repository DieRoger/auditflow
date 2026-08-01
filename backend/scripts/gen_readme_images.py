"""Generate README images: benchmark dashboard bar chart + pipeline funnel.

Output: auditflow/docs/images/*.png
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

IMG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "images")
os.makedirs(IMG_DIR, exist_ok=True)


def dashboard_chart():
    """Benchmark Dashboard — 横向柱状图"""
    metrics = [
        ("Review Reduction", 89.0, "#16a34a"),
        ("Evidence Reference Completeness", 100.0, "#16a34a"),
        ("Procedure Mapping Coverage", 100.0, "#16a34a"),
        ("Assessment Accuracy", 79.1, "#2563eb"),
        ("Assessment Balanced", 60.6, "#2563eb"),
        ("Detection F1", 60.1, "#d97706"),
        ("Workflow Success", 100.0, "#16a34a"),
    ]
    labels = [m[0] for m in metrics]
    values = [m[1] for m in metrics]
    colors = [m[2] for m in metrics]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(labels, values, color=colors, height=0.6)
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=10, color="#334155")

    ax.set_xlim(0, 115)
    ax.set_xlabel("Score (%)", fontsize=10)
    ax.set_title("AuditFlow Benchmark Dashboard v1.0 (Kaggle #1, 7,000 transactions)",
                 fontsize=12, fontweight="bold", pad=12)
    ax.axvline(80, color="#94a3b8", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(80.5, -0.7, "80% target", fontsize=8, color="#94a3b8")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    path = os.path.join(IMG_DIR, "benchmark_dashboard.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


def funnel_chart():
    """Pipeline Funnel — Review Reduction 可视化"""
    stages = [
        ("7000\nTransactions", 7000, "#1e293b"),
        ("769\nReview Queue\n(89% reduction)", 769, "#2563eb"),
        ("11535\nFindings", 11535, "#7c3aed"),
        ("3138\nHigh-Risk Items", 3138, "#d97706"),
        ("11535\nProcedures Planned", 11535, "#16a34a"),
    ]
    max_w = 7000

    fig, ax = plt.subplots(figsize=(8, 5))
    y_positions = list(range(len(stages)))[::-1]
    for y, (label, value, color) in zip(y_positions, stages):
        width = value / max_w
        ax.barh(y, width, height=0.6, color=color, alpha=0.9)
        ax.text(width + 0.01, y, label.replace("\n", " · "),
                va="center", fontsize=10, color="#334155")

    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_xlim(0, 1.05)
    ax.set_title("Review Reduction Funnel — AI flags 769 of 7,000 for human review",
                 fontsize=12, fontweight="bold", pad=12)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    path = os.path.join(IMG_DIR, "pipeline_funnel.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


if __name__ == "__main__":
    dashboard_chart()
    funnel_chart()
