#!/usr/bin/env python3
"""Nested participant-grouped EEG channel selection for the HALO capstone.

The script consumes the feature table created by extract_hinss_bandpower.py.
Selection is repeated inside each outer-training fold; held-out participants do
not influence screening, backward selection, scaling, or hyperparameters.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, GridSearchCV, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CHU_26 = [
    "P4", "PO6", "O1", "P6", "PO5", "P8", "PO8", "P7", "PO7", "PO4",
    "P5", "P1", "O2", "CP2", "P2", "AF3", "C1", "P3", "Pz", "C2",
    "PO3", "TP8", "Oz", "CP4", "TP7", "CP6",
]

PRIOR_CONFIGS = {
    "Prior-balanced-10": ["AF3", "AF4", "F3", "F4", "FCz", "P3", "P4", "POz", "O1", "O2"],
    "Prior-balanced-8": ["F3", "F4", "FCz", "P3", "P4", "O1", "O2", "Oz"],
    "Prior-balanced-6": ["Fz", "FCz", "P3", "P4", "O1", "O2"],
}

TARGET_COUNTS = (16, 10, 8, 6)
META_COLUMNS = {
    "subject", "session", "label", "epoch_in_block", "onset_seconds",
    "gross_bad_channel_fraction",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("results/channel_selection"))
    parser.add_argument("--outer-splits", type=int, default=5)
    parser.add_argument("--inner-splits", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=26)
    parser.add_argument("--random-state", type=int, default=461)
    parser.add_argument(
        "--bands",
        nargs="+",
        default=["theta", "alpha", "beta"],
        choices=["theta", "alpha", "beta", "theta_alpha"],
    )
    return parser.parse_args()


def feature_channel(column: str) -> str:
    return column.split("__", maxsplit=1)[0]


def feature_band(column: str) -> str:
    return column.split("__", maxsplit=1)[1]


def feature_columns(frame: pd.DataFrame, bands: list[str]) -> list[str]:
    return [
        c for c in frame.columns
        if c not in META_COLUMNS and "__" in c and feature_band(c) in bands
    ]


def columns_for_channels(columns: list[str], channels: list[str]) -> list[str]:
    wanted = set(channels)
    return [c for c in columns if feature_channel(c) in wanted]


def region(channel: str) -> str:
    if channel.startswith(("Fp", "AF", "FT", "F")):
        return "anterior"
    if channel.startswith(("FC", "C")):
        return "central"
    return "posterior"


def preserves_minimum_coverage(channels: list[str]) -> bool:
    counts = Counter(region(ch) for ch in channels)
    return counts["anterior"] >= 1 and counts["posterior"] >= 2


def selection_model() -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=3000,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def screen_channels(
    x: pd.DataFrame,
    y: np.ndarray,
    columns: list[str],
    max_candidates: int,
    random_state: int,
) -> tuple[list[str], pd.DataFrame]:
    mi = mutual_info_classif(x[columns], y, random_state=random_state)
    feature_scores = pd.DataFrame(
        {
            "feature": columns,
            "channel": [feature_channel(c) for c in columns],
            "mutual_information": mi,
        }
    )
    channel_scores = (
        feature_scores.groupby("channel", as_index=False)["mutual_information"]
        .mean()
        .sort_values("mutual_information", ascending=False)
    )

    selected = channel_scores.head(max_candidates)["channel"].tolist()
    # Ensure every broad scalp region is represented before backward selection.
    for required_region in ("anterior", "central", "posterior"):
        if not any(region(ch) == required_region for ch in selected):
            replacement = next(
                ch for ch in channel_scores["channel"] if region(ch) == required_region
            )
            selected[-1] = replacement
    return list(dict.fromkeys(selected)), channel_scores


def grouped_score(
    x: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    columns: list[str],
    channels: list[str],
    splits: int,
) -> float:
    cv = GroupKFold(n_splits=splits)
    scores = cross_val_score(
        selection_model(),
        x[columns_for_channels(columns, channels)],
        y,
        groups=groups,
        cv=cv,
        scoring="balanced_accuracy",
        n_jobs=-1,
    )
    return float(np.mean(scores))


def backward_path(
    x: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    columns: list[str],
    initial_channels: list[str],
    inner_splits: int,
) -> tuple[dict[int, list[str]], pd.DataFrame]:
    current = initial_channels.copy()
    saved: dict[int, list[str]] = {}
    history: list[dict[str, object]] = []

    while len(current) >= min(TARGET_COUNTS):
        if len(current) in TARGET_COUNTS:
            saved[len(current)] = current.copy()
        if len(current) == min(TARGET_COUNTS):
            break

        candidates: list[tuple[float, str]] = []
        for removed in current:
            reduced = [ch for ch in current if ch != removed]
            if not preserves_minimum_coverage(reduced):
                continue
            score = grouped_score(x, y, groups, columns, reduced, inner_splits)
            candidates.append((score, removed))
        if not candidates:
            raise RuntimeError("No valid channel removal preserved coverage constraints")
        best_score, removed = max(candidates, key=lambda item: (item[0], item[1]))
        history.append(
            {
                "channels_before": len(current),
                "removed": removed,
                "inner_balanced_accuracy_after_removal": best_score,
            }
        )
        current.remove(removed)

    return saved, pd.DataFrame(history)


def fit_and_test(
    train: pd.DataFrame,
    test: pd.DataFrame,
    columns: list[str],
    channels: list[str],
    inner_splits: int,
) -> dict[str, float]:
    chosen = columns_for_channels(columns, channels)
    if not chosen:
        raise ValueError("Configuration has no matching features")
    inner_groups = train["subject"].to_numpy()
    inner = GroupKFold(n_splits=inner_splits)
    model = GridSearchCV(
        selection_model(),
        {"model__C": [0.01, 0.1, 1.0, 10.0]},
        scoring="balanced_accuracy",
        cv=inner.split(train[chosen], train["label"], inner_groups),
        n_jobs=-1,
        refit=True,
    )
    model.fit(train[chosen], train["label"])
    predicted = model.predict(test[chosen])
    return {
        "balanced_accuracy": balanced_accuracy_score(test["label"], predicted),
        "macro_f1": f1_score(test["label"], predicted, average="macro"),
        "best_C": float(model.best_params_["model__C"]),
    }


def plot_performance(results: pd.DataFrame, destination: Path) -> None:
    selected = results[results["configuration"].str.startswith("Selected-")].copy()
    selected["channel_count"] = selected["channel_count"].astype(int)
    summary = selected.groupby("channel_count")["balanced_accuracy"].agg(["mean", "std"]).reset_index()
    summary = summary.sort_values("channel_count")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    ax.errorbar(
        summary["channel_count"], summary["mean"], yerr=summary["std"],
        marker="o", capsize=4, linewidth=2,
    )
    ax.axhline(1 / 3, color="0.5", linestyle="--", label="Chance (3 classes)")
    ax.set(xlabel="Recording channels", ylabel="Participant-independent balanced accuracy")
    ax.set_xticks(sorted(summary["channel_count"].unique()))
    ax.legend(frameon=False)
    sns.despine(fig=fig, ax=ax)
    fig.tight_layout()
    fig.savefig(destination, dpi=220)
    plt.close(fig)


def plot_redundancy(frame: pd.DataFrame, columns: list[str], destination: Path) -> None:
    alpha = [c for c in columns if feature_band(c) == "alpha"]
    aggregated = frame.groupby(["subject", "session", "label"], as_index=False)[alpha].mean()
    matrix = aggregated[alpha].rename(columns=feature_channel).corr(method="spearman")
    grid = sns.clustermap(matrix, cmap="vlag", center=0, vmin=-1, vmax=1, figsize=(11, 11))
    grid.fig.suptitle("Posterior/whole-scalp alpha-feature redundancy", y=1.02)
    grid.fig.savefig(destination, dpi=200, bbox_inches="tight")
    plt.close(grid.fig)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.features)
    columns = feature_columns(frame, args.bands)
    all_channels = sorted({feature_channel(c) for c in columns})
    chu_overlap = [ch for ch in CHU_26 if ch in all_channels]

    outer = GroupKFold(n_splits=args.outer_splits)
    rows: list[dict[str, object]] = []
    selection_rows: list[dict[str, object]] = []
    stability_rows: list[dict[str, object]] = []

    for fold, (train_index, test_index) in enumerate(
        outer.split(frame, frame["label"], frame["subject"]), start=1
    ):
        train = frame.iloc[train_index].reset_index(drop=True)
        test = frame.iloc[test_index].reset_index(drop=True)
        screened, screening = screen_channels(
            train[columns], train["label"].to_numpy(), columns,
            args.max_candidates, args.random_state + fold,
        )
        screening.assign(outer_fold=fold).to_csv(
            args.output_dir / f"screening_fold-{fold}.csv", index=False
        )
        selected, history = backward_path(
            train[columns], train["label"].to_numpy(), train["subject"].to_numpy(),
            columns, screened, args.inner_splits,
        )
        history.assign(outer_fold=fold).to_csv(
            args.output_dir / f"backward_history_fold-{fold}.csv", index=False
        )

        configurations: dict[str, list[str]] = {
            "Full-61": all_channels,
            "Chu-overlap-24": chu_overlap,
            **PRIOR_CONFIGS,
            **{f"Selected-{count}": channels for count, channels in selected.items()},
        }
        for name, channels in configurations.items():
            missing = sorted(set(channels) - set(all_channels))
            if missing:
                continue
            metrics = fit_and_test(train, test, columns, channels, args.inner_splits)
            rows.append(
                {
                    "outer_fold": fold,
                    "configuration": name,
                    "channel_count": len(channels),
                    "channels": " ".join(channels),
                    "test_subjects": " ".join(sorted(test["subject"].unique())),
                    **metrics,
                }
            )
        for count, channels in selected.items():
            for channel in channels:
                stability_rows.append(
                    {"outer_fold": fold, "channel_count": count, "channel": channel}
                )

    results = pd.DataFrame(rows)
    results.to_csv(args.output_dir / "outer_fold_results.csv", index=False)
    summary = (
        results.groupby(["configuration", "channel_count"], as_index=False)
        .agg(
            mean_balanced_accuracy=("balanced_accuracy", "mean"),
            sd_balanced_accuracy=("balanced_accuracy", "std"),
            mean_macro_f1=("macro_f1", "mean"),
        )
        .sort_values(["channel_count", "mean_balanced_accuracy"], ascending=[False, False])
    )
    summary.to_csv(args.output_dir / "performance_summary.csv", index=False)

    stability = pd.DataFrame(stability_rows)
    stability_summary = (
        stability.groupby(["channel_count", "channel"], as_index=False)
        .agg(selection_folds=("outer_fold", "nunique"))
    )
    stability_summary["selection_frequency"] = (
        stability_summary["selection_folds"] / args.outer_splits
    )
    stability_summary.to_csv(args.output_dir / "selection_stability.csv", index=False)

    plot_performance(results, args.output_dir / "performance_vs_channel_count.png")
    plot_redundancy(frame, columns, args.output_dir / "alpha_redundancy_heatmap.png")

    # Final recommendation path: fit on all participants only after unbiased outer evaluation.
    final_screened, final_screening = screen_channels(
        frame[columns], frame["label"].to_numpy(), columns,
        args.max_candidates, args.random_state,
    )
    final_selected, final_history = backward_path(
        frame[columns], frame["label"].to_numpy(), frame["subject"].to_numpy(),
        columns, final_screened, args.inner_splits,
    )
    final_screening.to_csv(args.output_dir / "final_screening_all_data.csv", index=False)
    final_history.to_csv(args.output_dir / "final_backward_history_all_data.csv", index=False)
    pd.DataFrame(
        [
            {"configuration": f"Selected-{count}", "channels": " ".join(channels)}
            for count, channels in sorted(final_selected.items(), reverse=True)
        ]
    ).to_csv(args.output_dir / "final_candidate_montages.csv", index=False)

    print(summary.to_string(index=False))
    print(f"\nSaved results to {args.output_dir}")


if __name__ == "__main__":
    main()
