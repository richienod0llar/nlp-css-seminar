#!/usr/bin/env python3
"""
Generate publication-quality figures from baseline eval artifacts.

Usage:
  python scripts/generate_figures.py
  python scripts/generate_figures.py --baseline-dir docs/baseline --run-id 20260625_134833

Outputs PDF + PNG to docs/figures/ (vector PDF preferred for papers).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

import seaborn as sns

# Project root on path when run as script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.sig.gold_fixes import EXCLUDED_EXAMPLE_IDS, apply_gold_corrections  # noqa: E402
from src.sig.normalize import extract_structure_code  # noqa: E402

# ---------------------------------------------------------------------------
# Publication style (single-column ~3.5 in, double-column ~7 in @ 300 dpi)
# ---------------------------------------------------------------------------
STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica", "Liberation Sans"],
    "font.size": 9,
    "axes.labelsize": 10,
    "axes.titlesize": 10,
    "axes.titleweight": "bold",
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
}

# Colorblind-friendly (Wong / Paul Tol inspired)
C_CONCEPT = "#0173B2"
C_STRUCTURE = "#DE8F05"
C_BOTH = "#029E73"
C_QUESTION = "#CC78BC"
C_NEUTRAL = "#949494"

# Qwen2.5-72B-Instruct was deleted from the shared model store after Run 5, so
# every external-judge figure from Run 7 on is produced by Qwen3-32B. Keep the
# name in one place: silently relabelling a changed instrument is how figures
# start lying.
EXT_JUDGE_NAME = "Qwen3-32B"

RUN_LABELS = {
    "20260620_185119": "Run 1\n(Initial)",
    "20260620_194152": "Run 2\n(Prompt)",
    "20260625_134833": "Run 3\n(Struct v1)",
    "20260703_180434": "Run 6\n(Struct v2)",
    "v6repro_20260824_101855": "Run 7a\n(YAML fix)",
    "v7a_20260824_102619": "Run 7b\n(De-leaked)",
    "v7b_20260824_103350": "Run 7c\n(+Notation)",
}

RUN_ORDER = [
    "20260620_185119",
    "20260620_194152",
    "20260625_134833",
    "20260703_180434",
    "v6repro_20260824_101855",
    "v7a_20260824_102619",
    "v7b_20260824_103350",
]


def _save(fig: plt.Figure, out_dir: Path, stem: str, tight: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # tight=False keeps the exact figsize canvas (no content-based cropping), so
    # sibling figures stay pixel-identical regardless of label lengths. Passing
    # bbox_inches=None falls back to the rcParam ("tight"), so build an explicit
    # full-canvas Bbox instead.
    from matplotlib.transforms import Bbox

    bbox = "tight" if tight else Bbox([[0, 0], fig.get_size_inches()])
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"{stem}.{ext}", bbox_inches=bbox)
    plt.close(fig)


def load_run_summaries(baseline_dir: Path) -> pd.DataFrame:
    """Headline metrics per run, recomputed on the corrected 113-item gold set.

    The eval_summary_*.json files were written at run time against the
    uncorrected 115-item gold set, so they are NOT used for the accuracy
    figures -- reading them would put n=115 numbers in the figures and n=113
    numbers in the text. Only the question-level fields, which the gold
    corrections do not touch, are still taken from the summary.
    """
    gold = pd.read_excel(ROOT / "data" / "gold_set.xlsx")
    rows = []
    for run_id in RUN_ORDER:
        summary_path = baseline_dir / f"eval_summary_vllm_{run_id}.json"
        report_path = baseline_dir / f"eval_report_vllm_{run_id}.csv"
        if not report_path.exists():
            continue
        data = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
        df = apply_gold_corrections(pd.read_csv(report_path), gold)
        concept = df["concept_accuracy"].astype(bool)
        structure = df["structure_accuracy"].astype(bool)
        rows.append({
            "run_id": run_id,
            "label": RUN_LABELS.get(run_id, run_id),
            "concept_accuracy_pct": round(concept.mean() * 100, 2),
            "structure_accuracy_pct": round(structure.mean() * 100, 2),
            "both_correct_pct": round((concept & structure).mean() * 100, 2),
            "question_non_empty_pct": data.get("question_non_empty_pct"),
            "question_exact_match_pct": data.get("question_exact_match_pct"),
            "n_items": len(df),
        })
    return pd.DataFrame(rows)


def fig01_run_progression(summary_df: pd.DataFrame, out_dir: Path) -> None:
    """Grouped bars: assertion metrics across three prompt-engineering iterations."""
    metrics = [
        ("concept_accuracy_pct", "Concept", C_CONCEPT),
        ("structure_accuracy_pct", "Structure", C_STRUCTURE),
        ("both_correct_pct", "Both correct", C_BOTH),
    ]
    x = np.arange(len(summary_df))
    width = 0.24
    # Sized for four runs originally; Run 7 adds three arms, so grow the canvas
    # rather than letting the tick labels overlap.
    fig, ax = plt.subplots(figsize=(6.5 + 0.85 * max(0, len(summary_df) - 4), 3.5))
    for i, (col, label, color) in enumerate(metrics):
        offset = (i - 1) * width
        bars = ax.bar(
            x + offset,
            summary_df[col],
            width,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.5,
        )
        for bar in bars:
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 1.2,
                f"{h:.0f}%",
                ha="center",
                va="bottom",
                fontsize=6,
            )
    ax.set_ylabel("Accuracy (%)")
    ax.set_xlabel("Evaluation run")
    ax.set_title("Assertion stage accuracy across prompt-engineering runs")
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["label"], fontsize=8)
    ax.set_ylim(0, 95)
    ax.legend(loc="upper left", frameon=False, ncol=3)
    ax.axhline(50, color=C_NEUTRAL, linestyle="--", linewidth=0.8, alpha=0.6, zorder=0)
    _save(fig, out_dir, "fig01_run_progression")


def fig02_pipeline_stages(summary_path: Path, out_dir: Path) -> None:
    """Compare assertion vs question-stage outcomes; include judge means when present."""
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    labels = [
        "Concept\naccuracy",
        "Structure\naccuracy",
        "Both\ncorrect",
        "Question\nnon-empty",
        "Question\nexact match",
    ]
    values = [
        data["concept_accuracy_pct"],
        data["structure_accuracy_pct"],
        data.get("both_correct_pct", 0),
        data["question_non_empty_pct"],
        data["question_exact_match_pct"],
    ]
    colors = [C_CONCEPT, C_STRUCTURE, C_BOTH, C_QUESTION, C_NEUTRAL]
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5)
    for bar, v in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            v + 1.5,
            f"{v:.1f}%",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    ax.set_ylabel("Rate (%)")
    title = "Isolated evaluation outcomes"
    if data.get("mean_assertion_question_score") is not None:
        title += (
            f" (judge: IA={data['mean_indicator_assertion_score']:.2f}, "
            f"AQ={data['mean_assertion_question_score']:.2f} /5)"
        )
    ax.set_title(title)
    ax.set_ylim(0, 108)
    _save(fig, out_dir, "fig02_pipeline_stages")


def fig03_per_concept_accuracy(summary_path: Path, out_dir: Path) -> None:
    """Per-concept concept vs structure accuracy (Run 3)."""
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    per = data.get("per_concept", {})
    if not per:
        return
    records = [
        {
            "concept": name,
            "n": v["n"],
            "concept_acc": v["concept_accuracy_pct"],
            "structure_acc": v["structure_accuracy_pct"],
        }
        for name, v in per.items()
    ]
    df = pd.DataFrame(records).sort_values("concept_acc", ascending=True)
    y = np.arange(len(df))
    height = 0.36
    fig_h = max(4.5, 0.22 * len(df))
    fig, ax = plt.subplots(figsize=(6.5, fig_h))
    ax.barh(y - height / 2, df["concept_acc"], height, label="Concept", color=C_CONCEPT)
    ax.barh(y + height / 2, df["structure_acc"], height, label="Structure", color=C_STRUCTURE)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{r.concept} (n={int(r.n)})" for r in df.itertuples()])
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Per-concept accuracy (gold concept labels)")
    ax.set_xlim(0, 105)
    ax.legend(loc="lower right", frameon=False)
    _save(fig, out_dir, "fig03_per_concept_accuracy")


def fig04_concept_confusion_heatmap(report_path: Path, out_dir: Path) -> None:
    """Row-normalized concept confusion matrix (errors visible off-diagonal)."""
    df = pd.read_csv(report_path)
    gold_order = sorted(df["gold_concept"].unique(), key=str)
    pred_order = sorted(df["pred_concept"].dropna().unique(), key=str)
    # Keep matrix readable: only concepts appearing in gold set
    ct = pd.crosstab(df["gold_concept"], df["pred_concept"])
    ct = ct.reindex(index=gold_order, columns=pred_order, fill_value=0)
    row_pct = ct.div(ct.sum(axis=1).replace(0, np.nan), axis=0) * 100
    # Mask zero cells for cleaner heatmap
    mask = ct == 0
    fig_w = max(8, 0.35 * len(pred_order))
    fig_h = max(7, 0.28 * len(gold_order))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    sns.heatmap(
        row_pct,
        annot=ct.values,
        fmt="d",
        cmap="Blues",
        mask=mask,
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "Row % (of gold concept)"},
        ax=ax,
        vmin=0,
        vmax=100,
        annot_kws={"size": 6},
    )
    ax.set_xlabel("Predicted concept")
    ax.set_ylabel("Gold concept")
    ax.set_title("Concept classification confusion (counts; color = row %)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    _save(fig, out_dir, "fig04_concept_confusion_heatmap")


def fig05_structure_confusion_heatmap(report_path: Path, out_dir: Path) -> None:
    """Structure-code confusion matrix (extracted codes)."""
    df = pd.read_csv(report_path)
    df = df.copy()
    df["gold_code"] = df["gold_structure"].map(extract_structure_code)
    df["pred_code"] = df["pred_structure"].map(extract_structure_code)
    df = df[df["gold_code"].astype(bool) & df["pred_code"].astype(bool)]
    gold_order = sorted(df["gold_code"].unique(), key=str)
    pred_order = sorted(df["pred_code"].unique(), key=str)
    ct = pd.crosstab(df["gold_code"], df["pred_code"])
    ct = ct.reindex(index=gold_order, columns=pred_order, fill_value=0)
    row_pct = ct.div(ct.sum(axis=1).replace(0, np.nan), axis=0) * 100
    mask = ct == 0
    fig_w = max(8, 0.4 * len(pred_order))
    fig_h = max(6, 0.35 * len(gold_order))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    sns.heatmap(
        row_pct,
        annot=ct.values,
        fmt="d",
        cmap="Oranges",
        mask=mask,
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "Row % (of gold structure)"},
        ax=ax,
        vmin=0,
        vmax=100,
        annot_kws={"size": 7},
    )
    ax.set_xlabel("Predicted structure code")
    ax.set_ylabel("Gold structure code")
    ax.set_title("Structure-code confusion (counts; color = row %)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    _save(fig, out_dir, "fig05_structure_confusion_heatmap")


def fig06_concept_structure_gap(summary_path: Path, out_dir: Path) -> None:
    """Scatter: concept vs structure accuracy per concept — highlights taxonomy paradox."""
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    per = data.get("per_concept", {})
    if not per:
        return
    df = pd.DataFrame(
        [
            {
                "concept": k,
                "n": v["n"],
                "concept_acc": v["concept_accuracy_pct"],
                "structure_acc": v["structure_accuracy_pct"],
                "gap": v["concept_accuracy_pct"] - v["structure_accuracy_pct"],
            }
            for k, v in per.items()
        ]
    )
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    sizes = 30 + df["n"] * 12
    ax.scatter(
        df["concept_acc"],
        df["structure_acc"],
        s=sizes,
        c=df["gap"],
        cmap="RdYlGn",
        vmin=-80,
        vmax=80,
        edgecolors="#333333",
        linewidths=0.4,
        alpha=0.85,
        zorder=3,
    )
    ax.plot([0, 100], [0, 100], "--", color=C_NEUTRAL, linewidth=1, label="Equal accuracy")

    # Label only the off-diagonal (interesting) concepts. Labels sit close to
    # their points with short connectors and a small vertical stagger so the
    # clustered low-structure points stay readable without long crossing lines.
    sel = df[(df["gap"].abs() >= 40) | ((df["concept_acc"] >= 80) & (df["structure_acc"] <= 20))]
    sel = sel.sort_values("concept_acc").reset_index(drop=True)
    # Small offsets (in display points) per label, tuned so neighbours land on
    # alternating rows. Keys are concept names for stable, predictable placement.
    offsets = {
        "Feelings": (0, 9, "center"),
        "Procedures": (0, 22, "center"),
        "Action tendencies": (-2, 9, "center"),
        "Expectations of future events": (-4, 40, "right"),
        "Evaluative belief": (-8, 6, "right"),
        "Policies": (10, 6, "left"),
    }
    for _, r in sel.iterrows():
        cx, cy = r["concept_acc"], r["structure_acc"]
        dx, dy, ha = offsets.get(r["concept"], (0, 10, "center"))
        ax.annotate(
            r["concept"],
            xy=(cx, cy),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=5.5,
            ha=ha,
            va="bottom",
            zorder=6,
            arrowprops=dict(arrowstyle="-", color="#b0b0b0", lw=0.45, shrinkA=0.5, shrinkB=2),
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.8),
        )
    ax.set_xlabel("Concept accuracy (%)")
    ax.set_ylabel("Structure accuracy (%)")
    ax.set_title("Concept–structure accuracy gap by basic concept")
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 110)
    ax.set_aspect("equal")
    sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=plt.Normalize(-80, 80))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Concept − structure (pp)")
    _save(fig, out_dir, "fig06_concept_structure_gap")


def fig07_top_confusion_pairs(confusion_path: Path, out_dir: Path, title: str, stem: str) -> None:
    """Horizontal bar chart of top misclassification pairs (readable alternative to large heatmaps)."""
    if not confusion_path.exists():
        return
    df = pd.read_csv(confusion_path)
    if df.empty:
        return
    df = df.sort_values("count", ascending=False).head(12)
    df["pair"] = df.iloc[:, 0].astype(str) + " → " + df.iloc[:, 1].astype(str)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    # Fixed margins (not tight bbox) so both fig07 charts share identical
    # canvas dimensions despite different y-label lengths.
    fig.subplots_adjust(left=0.34, right=0.96, top=0.88, bottom=0.15)
    y = np.arange(len(df))
    ax.barh(y, df["count"], color=C_STRUCTURE, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(df["pair"])
    ax.invert_yaxis()
    ax.set_xlabel("Count (misclassified rows)")
    ax.set_title(title)
    for i, (cnt, pair) in enumerate(zip(df["count"], df["pair"])):
        ax.text(cnt + 0.05, i, str(int(cnt)), va="center", fontsize=8)
    _save(fig, out_dir, stem, tight=False)


def fig08_judge_distributions(report_path: Path, out_dir: Path) -> None:
    """Histogram of LLM-as-judge alignment scores (1–5) for both stages."""
    df = pd.read_csv(report_path)
    if "indicator_assertion_score" not in df.columns:
        return
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2), sharey=True)
    for ax, col, title, color in [
        (axes[0], "indicator_assertion_score", "Indicator → assertion", C_CONCEPT),
        (axes[1], "assertion_question_score", "Assertion → question", C_QUESTION),
    ]:
        counts = df[col].dropna().astype(int).value_counts().sort_index()
        scores = list(range(1, 6))
        heights = [counts.get(s, 0) for s in scores]
        bars = ax.bar(scores, heights, color=color, edgecolor="white", linewidth=0.5)
        mean = df[col].mean()
        ax.axvline(mean, color="#333333", linestyle="--", linewidth=1, label=f"Mean={mean:.2f}")
        for bar, h in zip(bars, heights):
            if h:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 1, str(h), ha="center", fontsize=7)
        ax.set_xlabel("Judge score")
        ax.set_title(title)
        ax.set_xticks(scores)
        ax.set_xlim(0.5, 5.5)
        ax.legend(loc="upper left", frameon=False, fontsize=7)
    axes[0].set_ylabel(f"Number of rows (n={len(df)})")
    fig.suptitle("LLM-as-judge alignment score distributions", fontweight="bold", y=1.02)
    fig.tight_layout()
    _save(fig, out_dir, "fig08_judge_distributions")


def fig09_exact_match_vs_judge(report_path: Path, out_dir: Path) -> None:
    """Contrast misleading exact-match rate with judge-based question alignment."""
    df = pd.read_csv(report_path)
    if "assertion_question_score" not in df.columns:
        return
    exact_pct = df["question_exact_match"].mean() * 100
    judge_ge4_pct = (df["assertion_question_score"] >= 4).mean() * 100
    mean_aq = df["assertion_question_score"].mean()
    labels = ["Exact string\nmatch", "Judge score\n≥ 4", "Mean judge\nscore (/5)"]
    values = [exact_pct, judge_ge4_pct, mean_aq * 20]  # scale mean to 0–100 for viz
    display = [f"{exact_pct:.1f}%", f"{judge_ge4_pct:.1f}%", f"{mean_aq:.2f}"]
    colors = [C_NEUTRAL, C_QUESTION, C_BOTH]
    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.13)
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5, width=0.62)
    ax.set_ylabel("Rate (%)  ·  mean score ×20")
    ax.set_title("Question quality: exact match vs semantic judge")
    ax.set_ylim(0, 112)
    for bar, disp, val in zip(bars, display, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 2.5, disp, ha="center", fontsize=9)
    _save(fig, out_dir, "fig09_exact_match_vs_judge", tight=False)


def fig10_ia_by_concept_correctness(report_path: Path, out_dir: Path) -> None:
    """Judge indicator-assertion score when concept label is correct vs incorrect."""
    df = pd.read_csv(report_path)
    if "indicator_assertion_score" not in df.columns:
        return
    groups = [
        ("Concept correct", df[df["concept_accuracy"]], C_BOTH),
        ("Concept incorrect", df[~df["concept_accuracy"]], C_STRUCTURE),
    ]
    fig, ax = plt.subplots(figsize=(4.2, 3.5))
    positions = [1, 2]
    for pos, (label, sub, color) in zip(positions, groups):
        scores = sub["indicator_assertion_score"].dropna()
        parts = ax.violinplot(
            [scores],
            positions=[pos],
            showmeans=True,
            showmedians=True,
            widths=0.55,
        )
        for body in parts["bodies"]:
            body.set_facecolor(color)
            body.set_alpha(0.65)
        ax.scatter(
            [pos] * len(scores),
            scores,
            alpha=0.35,
            s=18,
            color=color,
            edgecolors="white",
            linewidths=0.3,
            zorder=3,
        )
        ax.text(pos, -0.35, f"{label}\nμ={scores.mean():.2f}, n={len(scores)}", ha="center", fontsize=8)
    ax.set_xticks([])
    ax.set_ylabel("Indicator → assertion judge score")
    ax.set_ylim(0.5, 5.4)
    ax.set_title("Assertion alignment vs taxonomy correctness")
    _save(fig, out_dir, "fig10_ia_by_concept_correctness")


def fig12_self_vs_external_judge(ext_report_path: Path, out_dir: Path) -> None:
    """Compare self-judge (9B) vs external judge mean alignment scores."""
    df = pd.read_csv(ext_report_path)
    required = {
        "indicator_assertion_score",
        "ext_indicator_assertion_score",
        "assertion_question_score",
        "ext_assertion_question_score",
    }
    if not required.issubset(df.columns):
        return
    metrics = [
        ("Indicator → assertion", "indicator_assertion_score", "ext_indicator_assertion_score"),
        ("Assertion → question", "assertion_question_score", "ext_assertion_question_score"),
    ]
    self_means = [df[self_col].mean() for _, self_col, _ in metrics]
    ext_means = [df[ext_col].mean() for _, _, ext_col in metrics]
    labels = [m[0] for m in metrics]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    bars_self = ax.bar(x - width / 2, self_means, width, label="Self (Qwen3.5-9B)", color=C_NEUTRAL)
    bars_ext = ax.bar(x + width / 2, ext_means, width, label=f"External ({EXT_JUDGE_NAME})", color=C_CONCEPT)
    ax.set_ylabel("Mean judge score (1–5)")
    ax.set_title("Self-judge vs external judge (Run 5)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(3.5, 5.15)
    ax.axhline(4, color="#cccccc", linestyle="--", linewidth=0.8)
    ax.legend(
        frameon=True,
        fancybox=False,
        edgecolor="#dddddd",
        framealpha=0.95,
        loc="upper left",
        fontsize=6.5,
        borderpad=0.3,
        handlelength=1.2,
        labelspacing=0.25,
    )
    for bars in (bars_self, bars_ext):
        for bar in bars:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.03,
                f"{bar.get_height():.2f}",
                ha="center",
                fontsize=8,
            )
    _save(fig, out_dir, "fig12_self_vs_external_judge", tight=False)


def fig13_ext_judge_distributions(ext_report_path: Path, out_dir: Path) -> None:
    """Histogram of external judge alignment scores."""
    df = pd.read_csv(ext_report_path)
    if "ext_indicator_assertion_score" not in df.columns:
        return
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2), sharey=True)
    for ax, col, title, color in [
        (axes[0], "ext_indicator_assertion_score", f"Indicator → assertion ({EXT_JUDGE_NAME})", C_CONCEPT),
        (axes[1], "ext_assertion_question_score", f"Assertion → question ({EXT_JUDGE_NAME})", C_QUESTION),
    ]:
        counts = df[col].dropna().astype(int).value_counts().sort_index()
        scores = list(range(1, 6))
        heights = [counts.get(s, 0) for s in scores]
        bars = ax.bar(scores, heights, color=color, edgecolor="white", linewidth=0.5)
        mean = df[col].mean()
        ax.axvline(mean, color="#333333", linestyle="--", linewidth=1, label=f"Mean={mean:.2f}")
        for bar, h in zip(bars, heights):
            if h:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 1, str(h), ha="center", fontsize=7)
        ax.set_xlabel("Judge score")
        ax.set_title(title)
        ax.set_xticks(scores)
        ax.set_xlim(0.5, 5.5)
        ax.legend(loc="upper left", frameon=False, fontsize=7)
    axes[0].set_ylabel(f"Number of rows (n={len(df)})")
    fig.suptitle(f"External judge ({EXT_JUDGE_NAME}) score distributions", fontweight="bold", y=1.02)
    fig.tight_layout()
    _save(fig, out_dir, "fig13_ext_judge_distributions")


def fig15_judge_degeneracy(baseline_dir: Path, out_dir: Path) -> None:
    """The W3 figure: two judges, the SAME generations, wildly different behaviour.

    Means are nearly identical (4.48 vs 4.43), which is exactly why they are the
    wrong summary. The 9B emits 5s and 2s and almost nothing else; the 32B uses
    the scale. Plotting them side by side is the whole argument in one panel.
    """
    sources = [
        ("Self-judge (Qwen3.5-9B)",
         baseline_dir / "eval_report_ext_judge_j9b_on_gen9b_vllm_v7b_20260824_103350_20260824_115228.csv",
         C_QUESTION),
        (f"External judge ({EXT_JUDGE_NAME})",
         baseline_dir / "eval_report_ext_judge_v7b_vllm_v7b_20260824_103350_20260824_112633.csv",
         C_CONCEPT),
    ]
    if not all(path.exists() for _, path, _ in sources):
        return

    fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.3), sharey=True)
    scores = list(range(1, 6))
    for ax, (title, path, color) in zip(axes, sources):
        df = pd.read_csv(path)
        df = df[~df["example_id"].isin(EXCLUDED_EXAMPLE_IDS)]
        ia = pd.to_numeric(df["ext_indicator_assertion_score"], errors="coerce")
        vals = ia.dropna()
        counts = vals.round().astype(int).value_counts()
        heights = [int(counts.get(sc, 0)) for sc in scores]
        bars = ax.bar(scores, heights, color=color, edgecolor="white", linewidth=0.5)
        for bar, h in zip(bars, heights):
            if h:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5, str(h),
                        ha="center", fontsize=7)
        ax.axvline(vals.mean(), color="#333333", linestyle="--", linewidth=1)
        # "scale points used" reads 4/5 for BOTH judges and hides the finding.
        # What separates them is the middle of the scale: the 9B jumps straight
        # from 2 to 5, so mid-scale occupancy is the discriminating statistic.
        mid = heights[2] + heights[3]  # scores 3 and 4
        note = (f"mean {vals.mean():.2f}  \u00b7  mid-scale (3\u20134): "
                f"{mid} of {len(vals)} ({mid / len(vals):.0%})")
        unparsed = int(ia.isna().sum())
        if unparsed:
            note += f"\n{unparsed} unparseable"
        ax.set_title(title, fontsize=9)
        ax.set_xlabel(f"Indicator \u2192 assertion score\n{note}", fontsize=8)
        ax.set_xticks(scores)
        ax.set_xlim(0.5, 5.5)

    axes[0].set_ylabel("Number of items (n=113)")
    fig.suptitle("The same 113 generations, judged by two models",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    _save(fig, out_dir, "fig15_judge_degeneracy")


def fig14_exact_match_vs_ext_judge(ext_report_path: Path, out_dir: Path) -> None:
    """Exact match vs external judge for question quality."""
    df = pd.read_csv(ext_report_path)
    if "ext_assertion_question_score" not in df.columns:
        return
    exact_pct = df["question_exact_match"].mean() * 100
    judge_ge4_pct = (df["ext_assertion_question_score"] >= 4).mean() * 100
    mean_aq = df["ext_assertion_question_score"].mean()
    labels = ["Exact string\nmatch", "Ext. judge\n≥ 4", "Mean ext.\njudge (/5)"]
    values = [exact_pct, judge_ge4_pct, mean_aq * 20]
    display = [f"{exact_pct:.1f}%", f"{judge_ge4_pct:.1f}%", f"{mean_aq:.2f}"]
    colors = [C_NEUTRAL, C_QUESTION, C_BOTH]
    fig, ax = plt.subplots(figsize=(5.0, 3.8))
    fig.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.13)
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5, width=0.62)
    ax.set_ylabel("Rate (%)  ·  mean score ×20")
    ax.set_title(f"Question quality: exact match vs external judge ({EXT_JUDGE_NAME})")
    ax.set_ylim(0, 112)
    for bar, disp, val in zip(bars, display, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 2.5, disp, ha="center", fontsize=9)
    _save(fig, out_dir, "fig14_exact_match_vs_ext_judge", tight=False)


def fig11_mean_ia_by_concept(report_path: Path, out_dir: Path) -> None:
    """Mean indicator-assertion judge score by gold concept."""
    df = pd.read_csv(report_path)
    if "indicator_assertion_score" not in df.columns:
        return
    grp = (
        df.groupby("gold_concept")
        .agg(n=("example_id", "count"), ia_mean=("indicator_assertion_score", "mean"))
        .sort_values("ia_mean")
    )
    y = np.arange(len(grp))
    fig_h = max(4.5, 0.22 * len(grp))
    fig, ax = plt.subplots(figsize=(6, fig_h))
    colors = [C_STRUCTURE if m < 4 else C_CONCEPT for m in grp["ia_mean"]]
    ax.barh(y, grp["ia_mean"], color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{idx} (n={int(r.n)})" for idx, r in grp.iterrows()])
    ax.set_xlabel("Mean indicator → assertion judge score (1–5)")
    ax.set_title("Assertion semantic alignment by gold concept")
    ax.set_xlim(1, 5.2)
    ax.axvline(4, color=C_NEUTRAL, linestyle="--", linewidth=0.8, alpha=0.7)
    _save(fig, out_dir, "fig11_mean_ia_by_concept")


def write_figures_readme(out_dir: Path) -> None:
    text = """# Figures for baseline evaluation report

Generated by `python scripts/generate_figures.py`. Use **PDF** versions in manuscripts; PNG for slides.

| File | Recommended use | Caption sketch |
|------|-----------------|----------------|
| `fig01_run_progression` | Main results | Assertion-stage accuracy across four prompt-engineering runs (Runs 1, 2, 3, 6). |
| `fig02_pipeline_stages` | Results / discussion | Comparison of assertion taxonomy metrics vs question-generation metrics (Run 6). |
| `fig03_per_concept_accuracy` | Results | Per-concept concept and structure accuracy; bar length shows performance on rare vs frequent categories. |
| `fig04_concept_confusion_heatmap` | Appendix or supplementary | Confusion matrix for basic concepts (cell counts; color = row-normalized %). |
| `fig05_structure_confusion_heatmap` | Appendix | Confusion matrix for semantic structure codes. |
| `fig06_concept_structure_gap` | Discussion | Concepts with high concept accuracy but low structure accuracy (off-diagonal from equality line). |
| `fig07_top_concept_confusions` | Discussion | Most frequent concept misclassification pairs. |
| `fig07_top_structure_confusions` | Discussion | Most frequent structure-code misclassification pairs. |
| `fig08_judge_distributions` | Results (Run 4) | Histogram of 1–5 alignment scores for indicator→assertion and assertion→question. |
| `fig09_exact_match_vs_judge` | Discussion | Why exact string match (18%) understates question quality (99% judge ≥4). |
| `fig10_ia_by_concept_correctness` | Discussion | Judge scores when concept label is correct vs incorrect. |
| `fig11_mean_ia_by_concept` | Appendix | Mean assertion alignment score by gold basic concept. |
| `fig12_self_vs_external_judge` | Results (Run 5/7) | Mean self-judge (9B) vs external judge (Qwen3-32B) scores. |
| `fig13_ext_judge_distributions` | Results (Run 5) | External judge score histograms for IA and AQ. |
| `fig14_exact_match_vs_ext_judge` | Discussion (Run 5) | Exact match vs external judge on question quality. |
| `fig15_judge_degeneracy` | Discussion (Run 7, **W3**) | Same 113 generations judged by the 9B and the 32B. Near-identical means, incompatible distributions: the self-judge uses 2 of 5 scale points. |

Pass `--run-id 20260703_180434` for Run 6 objective figures (default). Pass `--judge-run-id 20260625_160020` for judge figures (Run 4). Pass `--ext-judge-report` for Run 5 external judge figures.

## Regenerating

```bash
cd ~/nlp-css-seminar
source scripts/activate_env.sh
pip install matplotlib seaborn  # if needed
python scripts/generate_figures.py
```
"""
    (out_dir / "FIGURES.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate publication figures from baseline evals.")
    parser.add_argument("--baseline-dir", type=Path, default=ROOT / "docs" / "baseline")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs" / "figures")
    parser.add_argument(
        "--run-id",
        default="v7b_20260824_103350",
        help="Run ID for detailed figures (Run 6 default); judge figs use Run 4 report",
    )
    parser.add_argument(
        "--judge-run-id",
        default="20260625_160020",
        help="Run ID for self-judge figures fig08–fig11",
    )
    parser.add_argument(
        "--ext-judge-report",
        type=Path,
        default=ROOT / "docs" / "baseline" / "eval_report_ext_judge_run4_32b_vllm_20260625_160020_20260824_110758.csv",
        help="Run 5 external judge report CSV (self + ext columns)",
    )
    args = parser.parse_args()

    plt.rcParams.update(STYLE)
    sns.set_theme(style="white", font_scale=0.95)

    summary_df = load_run_summaries(args.baseline_dir)
    if summary_df.empty:
        raise SystemExit(f"No summaries found in {args.baseline_dir}")

    run_summary = args.baseline_dir / f"eval_summary_vllm_{args.run_id}.json"
    run_report = args.baseline_dir / f"eval_report_vllm_{args.run_id}.csv"
    judge_report = args.baseline_dir / f"eval_report_vllm_{args.judge_run_id}.csv"
    concept_conf = args.baseline_dir / f"concept_confusion_vllm_{args.run_id}.csv"
    struct_conf = args.baseline_dir / f"structure_confusion_vllm_{args.run_id}.csv"

    print(f"Generating figures → {args.out_dir.resolve()}")
    fig01_run_progression(summary_df, args.out_dir)
    if run_summary.exists():
        fig02_pipeline_stages(run_summary, args.out_dir)
        fig03_per_concept_accuracy(run_summary, args.out_dir)
        fig06_concept_structure_gap(run_summary, args.out_dir)
    if run_report.exists():
        fig04_concept_confusion_heatmap(run_report, args.out_dir)
        fig05_structure_confusion_heatmap(run_report, args.out_dir)
    fig07_top_confusion_pairs(
        concept_conf,
        args.out_dir,
        "Top concept misclassification pairs",
        "fig07_top_concept_confusions",
    )
    fig07_top_confusion_pairs(
        struct_conf,
        args.out_dir,
        "Top structure-code misclassification pairs",
        "fig07_top_structure_confusions",
    )
    if judge_report.exists():
        fig08_judge_distributions(judge_report, args.out_dir)
        fig09_exact_match_vs_judge(judge_report, args.out_dir)
        fig10_ia_by_concept_correctness(judge_report, args.out_dir)
        fig11_mean_ia_by_concept(judge_report, args.out_dir)
    if args.ext_judge_report.exists():
        fig12_self_vs_external_judge(args.ext_judge_report, args.out_dir)
        fig13_ext_judge_distributions(args.ext_judge_report, args.out_dir)
        fig14_exact_match_vs_ext_judge(args.ext_judge_report, args.out_dir)
    fig15_judge_degeneracy(args.baseline_dir, args.out_dir)
    write_figures_readme(args.out_dir)
    print("Done. See docs/figures/FIGURES.md for caption guidance.")


if __name__ == "__main__":
    main()
