#!/usr/bin/env python3
"""Recover participant-level scores and bootstrap uncertainty for completed folds."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


META_COLUMNS = {
    "subject", "session", "label", "epoch_in_block", "onset_seconds",
    "gross_bad_channel_fraction",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--fold-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--outer-splits", type=int, default=5)
    parser.add_argument("--bootstrap-repetitions", type=int, default=10_000)
    parser.add_argument("--random-state", type=int, default=461)
    return parser.parse_args()


def bootstrap_mean_ci(values: np.ndarray, repetitions: int, rng: np.random.Generator) -> tuple[float, float]:
    draws = rng.choice(values, size=(repetitions, len(values)), replace=True).mean(axis=1)
    return float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.features)
    folds = pd.read_csv(args.fold_results)
    columns = [
        c for c in frame.columns
        if c not in META_COLUMNS and c.endswith(("__theta", "__alpha", "__beta"))
    ]

    outer = GroupKFold(n_splits=args.outer_splits)
    fold_indices = {
        fold: (train_index, test_index)
        for fold, (train_index, test_index) in enumerate(
            outer.split(frame, frame["label"], frame["subject"]), start=1
        )
    }

    participant_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    for result in folds.itertuples(index=False):
        train_index, test_index = fold_indices[int(result.outer_fold)]
        train = frame.iloc[train_index]
        test = frame.iloc[test_index]
        channels = str(result.channels).split()
        chosen = [c for c in columns if c.split("__", 1)[0] in channels]
        model = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=float(result.best_C),
                        class_weight="balanced",
                        max_iter=3000,
                        solver="lbfgs",
                    ),
                ),
            ]
        )
        model.fit(train[chosen], train["label"])
        predicted = model.predict(test[chosen])
        prediction = test[["subject", "session", "label"]].copy()
        prediction["predicted"] = predicted
        prediction["outer_fold"] = int(result.outer_fold)
        prediction["configuration"] = result.configuration
        prediction_rows.extend(prediction.to_dict("records"))

        for subject, rows in prediction.groupby("subject"):
            participant_rows.append(
                {
                    "subject": subject,
                    "outer_fold": int(result.outer_fold),
                    "configuration": result.configuration,
                    "channel_count": int(result.channel_count),
                    "balanced_accuracy": balanced_accuracy_score(rows["label"], rows["predicted"]),
                    "macro_f1": f1_score(rows["label"], rows["predicted"], average="macro"),
                }
            )

    participant = pd.DataFrame(participant_rows)
    participant.to_csv(args.output_dir / "participant_results.csv", index=False)
    pd.DataFrame(prediction_rows).to_csv(args.output_dir / "epoch_predictions.csv.gz", index=False, compression="gzip")

    rng = np.random.default_rng(args.random_state)
    summary_rows: list[dict[str, object]] = []
    for (configuration, channel_count), rows in participant.groupby(["configuration", "channel_count"]):
        values = rows["balanced_accuracy"].to_numpy()
        low, high = bootstrap_mean_ci(values, args.bootstrap_repetitions, rng)
        summary_rows.append(
            {
                "configuration": configuration,
                "channel_count": channel_count,
                "participants": len(values),
                "mean_balanced_accuracy": values.mean(),
                "sd_across_participants": values.std(ddof=1),
                "bootstrap_95_ci_low": low,
                "bootstrap_95_ci_high": high,
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["channel_count", "mean_balanced_accuracy"], ascending=[False, False]
    )
    summary.to_csv(args.output_dir / "participant_bootstrap_summary.csv", index=False)

    pivot = participant.pivot(index="subject", columns="configuration", values="balanced_accuracy")
    difference_rows: list[dict[str, object]] = []
    for comparator in ("Full-61", "Selected-16"):
        if comparator not in pivot:
            continue
        for candidate in pivot.columns:
            if candidate == comparator:
                continue
            differences = (pivot[candidate] - pivot[comparator]).dropna().to_numpy()
            low, high = bootstrap_mean_ci(differences, args.bootstrap_repetitions, rng)
            difference_rows.append(
                {
                    "candidate": candidate,
                    "comparator": comparator,
                    "participants": len(differences),
                    "mean_accuracy_difference": differences.mean(),
                    "bootstrap_95_ci_low": low,
                    "bootstrap_95_ci_high": high,
                }
            )
    differences = pd.DataFrame(difference_rows)
    differences.to_csv(args.output_dir / "paired_accuracy_differences.csv", index=False)

    print(summary.to_string(index=False))
    print("\nPaired differences versus Selected-16:")
    print(differences[differences["comparator"] == "Selected-16"].to_string(index=False))


if __name__ == "__main__":
    main()

