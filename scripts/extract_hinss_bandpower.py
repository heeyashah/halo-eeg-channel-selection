#!/usr/bin/env python3
"""Extract participant/session-level EEG band-power features from NEMAR nm000343.

This script intentionally performs only a fixed, minimal preprocessing sequence.
It does not perform workload-informed channel rejection or channel selection.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

import mne
import numpy as np
import pandas as pd
from scipy.signal import welch


BANDS = {
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
}
WORKLOAD_LABELS = ("easy", "medium", "diff")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/hinss_bandpower_features.csv.gz"),
    )
    parser.add_argument("--epoch-seconds", type=float, default=4.0)
    parser.add_argument("--resample-hz", type=float, default=128.0)
    parser.add_argument("--subjects", nargs="*", default=None)
    return parser.parse_args()


def identifiers(path: Path) -> tuple[str, str]:
    match = re.search(r"(sub-[^/]+)/(?P<session>ses-[^/]+)", path.as_posix())
    if match is None:
        raise ValueError(f"Could not parse participant/session from {path}")
    return match.group(1), match.group("session")


def workload_blocks(events_path: Path) -> list[tuple[str, float, float]]:
    events = pd.read_csv(events_path, sep="\t", encoding="utf-8-sig")
    events = events[events["trial_type"].isin(WORKLOAD_LABELS)].copy()
    blocks: list[tuple[str, float, float]] = []
    for label in WORKLOAD_LABELS:
        rows = events[events["trial_type"] == label]
        if rows.empty:
            continue
        start = float(rows["onset"].min())
        stop = float((rows["onset"] + rows["duration"]).max())
        blocks.append((label, start, stop))
    return blocks


def integrate_band(psd: np.ndarray, freqs: np.ndarray, low: float, high: float) -> np.ndarray:
    mask = (freqs >= low) & (freqs < high)
    return np.trapezoid(psd[..., mask], freqs[mask], axis=-1)


def epoch_features(data: np.ndarray, sfreq: float, ch_names: list[str]) -> dict[str, float]:
    freqs, psd = welch(
        data,
        fs=sfreq,
        window="hann",
        nperseg=int(2 * sfreq),
        noverlap=int(sfreq),
        axis=-1,
    )
    total = integrate_band(psd, freqs, 1.0, 40.0)
    total = np.maximum(total, np.finfo(float).tiny)

    result: dict[str, float] = {}
    band_values: dict[str, np.ndarray] = {}
    for band, (low, high) in BANDS.items():
        power = integrate_band(psd, freqs, low, high)
        relative = np.maximum(power / total, np.finfo(float).tiny)
        values = np.log10(relative)
        band_values[band] = values
        result.update({f"{ch}__{band}": float(value) for ch, value in zip(ch_names, values)})

    ratio = np.log10(
        np.maximum(
            np.power(10.0, band_values["theta"]) / np.power(10.0, band_values["alpha"]),
            np.finfo(float).tiny,
        )
    )
    result.update({f"{ch}__theta_alpha": float(value) for ch, value in zip(ch_names, ratio)})
    return result


def process_recording(bdf_path: Path, epoch_seconds: float, resample_hz: float) -> pd.DataFrame:
    subject, session = identifiers(bdf_path)
    events_path = Path(str(bdf_path).replace("_eeg.bdf", "_events.tsv"))
    raw = mne.io.read_raw_bdf(bdf_path, preload=True, verbose="ERROR")
    raw.set_eeg_reference("average", projection=False, verbose="ERROR")
    raw.filter(1.0, 40.0, verbose="ERROR")
    raw.resample(resample_hz, verbose="ERROR")

    sfreq = float(raw.info["sfreq"])
    epoch_samples = int(round(epoch_seconds * sfreq))
    rows: list[dict[str, object]] = []

    for label, block_start, block_stop in workload_blocks(events_path):
        starts = np.arange(block_start, block_stop - epoch_seconds + 1e-9, epoch_seconds)
        for epoch_in_block, start in enumerate(starts):
            first = int(round(start * sfreq))
            last = first + epoch_samples
            data = raw.get_data(start=first, stop=last)
            if data.shape[1] != epoch_samples:
                continue

            # Fixed, label-blind gross-artifact rule. An epoch is excluded only if
            # more than 20% of channels exceed 300 microvolts peak-to-peak.
            channel_ptp = np.ptp(data, axis=1)
            bad_fraction = float(np.mean(channel_ptp > 300e-6))
            if bad_fraction > 0.20:
                continue

            row: dict[str, object] = {
                "subject": subject,
                "session": session,
                "label": label,
                "epoch_in_block": epoch_in_block,
                "onset_seconds": float(start),
                "gross_bad_channel_fraction": bad_fraction,
            }
            row.update(epoch_features(data, sfreq, raw.ch_names))
            rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    bdf_paths = sorted(args.data_root.glob("sub-*/ses-*/eeg/*_eeg.bdf"))
    if args.subjects:
        wanted = {s if s.startswith("sub-") else f"sub-{s}" for s in args.subjects}
        bdf_paths = [p for p in bdf_paths if identifiers(p)[0] in wanted]
    if not bdf_paths:
        raise SystemExit(f"No BDF recordings found under {args.data_root}")

    frames: list[pd.DataFrame] = []
    for index, path in enumerate(bdf_paths, start=1):
        print(f"[{index}/{len(bdf_paths)}] {path}", flush=True)
        frames.append(process_recording(path, args.epoch_seconds, args.resample_hz))

    features = pd.concat(frames, ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(args.output, index=False, compression="gzip")
    print(f"Saved {features.shape[0]} epochs x {features.shape[1]} columns to {args.output}")


if __name__ == "__main__":
    main()

