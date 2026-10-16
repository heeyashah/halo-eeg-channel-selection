#!/usr/bin/env python3
"""Create MDR-ready figures from the completed HALO channel analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
import mne
import numpy as np
import pandas as pd
import seaborn as sns


CHU_26 = [
    "P4", "PO6", "O1", "P6", "PO5", "P8", "PO8", "P7", "PO7", "PO4",
    "P5", "P1", "O2", "CP2", "P2", "AF3", "C1", "P3", "Pz", "C2",
    "PO3", "TP8", "Oz", "CP4", "TP7", "CP6",
]
PRIOR_8 = ["F3", "F4", "FCz", "P3", "P4", "O1", "O2", "Oz"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    return parser.parse_args()


def scalp_panel(ax: plt.Axes, available: list[str], selected: list[str], title: str, color: str) -> None:
    montage = mne.channels.make_standard_montage("colin27_1020")
    positions = montage.get_positions()["ch_pos"]
    usable = [ch for ch in available if ch in positions]
    xy = np.array([positions[ch][:2] for ch in usable])
    radius = float(np.max(np.linalg.norm(xy, axis=1)) * 1.08)
    ax.add_patch(Circle((0, 0), radius, facecolor="#f7f7f7", edgecolor="0.25", linewidth=1.5))
    ax.add_patch(
        Polygon(
            [[-0.012, radius * 0.98], [0, radius * 1.12], [0.012, radius * 0.98]],
            closed=False, fill=False, edgecolor="0.25", linewidth=1.5,
        )
    )
    ax.scatter(xy[:, 0], xy[:, 1], s=14, color="0.75", zorder=2)
    shown = [ch for ch in selected if ch in positions and ch in available]
    chosen_xy = np.array([positions[ch][:2] for ch in shown])
    ax.scatter(chosen_xy[:, 0], chosen_xy[:, 1], s=44, color=color, edgecolor="white", linewidth=0.6, zorder=3)
    for ch, (x, y) in zip(shown, chosen_xy):
        ax.text(x, y + radius * 0.035, ch, ha="center", va="bottom", fontsize=7, zorder=4)
    ax.set_title(title, fontsize=10)
    ax.set_aspect("equal")
    ax.set_xlim(-radius * 1.16, radius * 1.16)
    ax.set_ylim(-radius * 1.12, radius * 1.18)
    ax.axis("off")


def montage_figure(results_dir: Path, data_root: Path) -> None:
    channels_file = next(data_root.glob("sub-*/ses-*/eeg/*_channels.tsv"))
    available = pd.read_csv(channels_file, sep="\t", encoding="utf-8-sig")["name"].tolist()
    final = pd.read_csv(results_dir / "final_candidate_montages.csv")
    selected_8 = final.loc[final["configuration"] == "Selected-8", "channels"].iloc[0].split()
    chu_overlap = [ch for ch in CHU_26 if ch in available]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    scalp_panel(axes[0], available, chu_overlap, "Chu et al. overlap (24/26)", "#d95f02")
    scalp_panel(axes[1], available, PRIOR_8, "Balanced prior (8)", "#1b9e77")
    scalp_panel(axes[2], available, selected_8, "All-data selected candidate (8)", "#7570b3")
    fig.suptitle("Candidate EEG recording montages (reference/ground not shown)", y=1.02, fontsize=13)
    fig.tight_layout()
    fig.savefig(results_dir / "electrode_montage_comparison.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def performance_figure(results_dir: Path) -> None:
    summary = pd.read_csv(results_dir / "participant_bootstrap_summary.csv")
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    styles = {
        "selected": ("#7570b3", "o"),
        "prior": ("#1b9e77", "s"),
        "comparator": ("#d95f02", "D"),
    }
    for row in summary.itertuples(index=False):
        family = "prior" if str(row.configuration).startswith("Prior") else (
            "selected" if str(row.configuration).startswith("Selected") else "comparator"
        )
        color, marker = styles[family]
        low = row.mean_balanced_accuracy - row.bootstrap_95_ci_low
        high = row.bootstrap_95_ci_high - row.mean_balanced_accuracy
        ax.errorbar(
            row.channel_count, row.mean_balanced_accuracy,
            yerr=np.array([[low], [high]]), fmt=marker, color=color,
            markersize=7, capsize=3, alpha=0.95,
        )
        ax.annotate(
            str(row.configuration).replace("Prior-balanced-", "Prior-").replace("Chu-overlap-", "Chu-"),
            (row.channel_count, row.mean_balanced_accuracy), xytext=(5, 4),
            textcoords="offset points", fontsize=7,
        )
    ax.axhline(1 / 3, color="0.45", linestyle="--", linewidth=1, label="Chance")
    ax.set(
        xlabel="EEG recording channels (reference/ground excluded)",
        ylabel="Participant-independent balanced accuracy",
        title="Workload discrimination versus channel count",
    )
    ax.set_ylim(0.30, 0.52)
    ax.set_xscale("log", base=2)
    ax.set_xticks([6, 8, 10, 16, 24, 61], labels=[6, 8, 10, 16, 24, 61])
    sns.despine(fig=fig, ax=ax)
    fig.tight_layout()
    fig.savefig(results_dir / "performance_all_configurations.png", dpi=240)
    plt.close(fig)


def stability_figure(results_dir: Path) -> None:
    stability = pd.read_csv(results_dir / "selection_stability.csv")
    keep = stability.groupby("channel")["selection_frequency"].max()
    keep = keep[keep >= 0.4].index
    matrix = (
        stability[stability["channel"].isin(keep)]
        .pivot(index="channel", columns="channel_count", values="selection_frequency")
        .fillna(0)
    )
    matrix = matrix.reindex(columns=[16, 10, 8, 6])
    matrix = matrix.assign(maximum=matrix.max(axis=1)).sort_values("maximum", ascending=False).drop(columns="maximum")
    fig, ax = plt.subplots(figsize=(6.2, max(4.5, 0.28 * len(matrix))))
    sns.heatmap(matrix, cmap="crest", vmin=0, vmax=1, annot=True, fmt=".1f", ax=ax)
    ax.set(xlabel="Target channel count", ylabel="Electrode", title="Selection frequency across outer folds")
    fig.tight_layout()
    fig.savefig(results_dir / "selection_stability_heatmap.png", dpi=240)
    plt.close(fig)


def importance_figure(results_dir: Path) -> None:
    scores = pd.read_csv(results_dir / "final_screening_all_data.csv").head(20).copy()
    scores = scores.sort_values("mutual_information")
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    ax.barh(scores["channel"], scores["mutual_information"], color="#4c78a8")
    ax.set(
        xlabel="Mean mutual information across theta/alpha/beta features",
        ylabel="Electrode",
        title="Training-data channel screening (descriptive)",
    )
    sns.despine(fig=fig, ax=ax)
    fig.tight_layout()
    fig.savefig(results_dir / "channel_screening_importance.png", dpi=240)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    montage_figure(args.results_dir, args.data_root)
    performance_figure(args.results_dir)
    stability_figure(args.results_dir)
    importance_figure(args.results_dir)
    print(f"Saved report figures to {args.results_dir}")


if __name__ == "__main__":
    main()
