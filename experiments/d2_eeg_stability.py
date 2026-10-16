"""Exploratory D2 radius/embedding sensitivity on one BCI IV 2a GDF recording.

Example:
    python experiments/d2_eeg_stability.py --gdf "C:/path/BCICIV_2a_gdf/A01T.gdf"

This script is a diagnostic, not a validated clinical/neuroscientific estimator.
It analyzes C3, 8-30 Hz, 4-s epochs for left/right hand events only.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import mne
from scipy.spatial.distance import cdist
from scipy.stats import linregress

MNE_LOG_LEVEL = "ERROR"
CLASS_CODES = {769: "left_hand", 770: "right_hand"}


def delay_embedding(x: np.ndarray, m: int, tau: int) -> np.ndarray:
    n = len(x) - (m - 1) * tau
    if n < 100:
        raise ValueError("Epoch too short for embedding")
    return np.column_stack([x[j * tau:j * tau + n] for j in range(m)])


def slope_for_range(x: np.ndarray, m: int, tau: int, theiler: int,
                    q_low: float, q_high: float, n_radii: int = 50):
    emb = delay_embedding(x, m, tau)
    n = len(emb)
    i, j = np.triu_indices(n, k=theiler + 1)
    distances = cdist(emb, emb, metric="euclidean")[i, j]
    distances = distances[np.isfinite(distances) & (distances > 0)]
    if len(distances) < 100:
        return np.nan, np.nan, 0
    r_low, r_high = np.quantile(distances, [q_low, q_high])
    if not np.isfinite(r_low + r_high) or r_low <= 0 or r_high <= r_low:
        return np.nan, np.nan, 0
    radii = np.geomspace(r_low, r_high, n_radii)
    corr = np.array([(distances < r).mean() for r in radii])
    keep = (corr > 0) & np.isfinite(corr)
    if keep.sum() < 8:
        return np.nan, np.nan, int(keep.sum())
    fit = linregress(np.log(radii[keep]), np.log(corr[keep]))
    return float(fit.slope), float(fit.rvalue ** 2), int(keep.sum())


def event_codes(raw: mne.io.BaseRaw):
    events, mapping = mne.events_from_annotations(raw, verbose=MNE_LOG_LEVEL)
    target = {}
    for description, code in mapping.items():
        text = str(description).strip()
        # GDF annotations are commonly represented as '769', etc.
        if text.isdigit() and int(text) in CLASS_CODES:
            target[text] = int(code)
    if not target:
        raise RuntimeError(
            "Could not find event annotations 769/770. Found annotation mapping: "
            + repr(mapping)
        )
    return events, target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gdf", required=True, help="Path to a training GDF file such as A01T.gdf")
    parser.add_argument("--max-epochs-per-class", type=int, default=8)
    parser.add_argument("--channels", default="C3", help="Comma-separated EEG channel names; default C3")
    parser.add_argument("--out", default=None, help="Output directory; default results/d2_eeg_stability")
    args = parser.parse_args()
    gdf_path = Path(args.gdf).expanduser().resolve()
    if not gdf_path.is_file():
        raise FileNotFoundError(f"GDF not found: {gdf_path}")
    out_dir = Path(args.out).expanduser().resolve() if args.out else Path(__file__).resolve().parents[1] / "results" / "d2_eeg_stability"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = mne.io.read_raw_gdf(str(gdf_path), preload=True, verbose=MNE_LOG_LEVEL)
    events, target = event_codes(raw)
    picks = [ch.strip() for ch in args.channels.split(",") if ch.strip()]
    missing = [ch for ch in picks if ch not in raw.ch_names]
    if missing:
        # GDF channel labels can include an EEG- prefix; try a suffix match.
        matched = []
        for wanted in picks:
            candidates = [c for c in raw.ch_names if c.upper().endswith(wanted.upper())]
            if candidates:
                matched.append(candidates[0])
        if len(matched) != len(picks):
            raise ValueError(f"Channels not found: {missing}. Available channels: {raw.ch_names}")
        picks = matched

    sfreq = float(raw.info["sfreq"])
    raw.filter(8.0, 30.0, picks=picks, verbose=MNE_LOG_LEVEL)
    event_id = {desc: code for desc, code in target.items()}
    epochs = mne.Epochs(raw, events, event_id=event_id, tmin=0.0,
                        tmax=4.0 - 1.0 / sfreq, baseline=None, preload=True,
                        picks=picks, reject_by_annotation=True, verbose=MNE_LOG_LEVEL)
    print(f"Input: {gdf_path}")
    print(f"Sampling frequency: {sfreq:g} Hz; channels: {picks}; filter: 8-30 Hz; epoch: 0-4 s")
    print(f"Recognized events: {target}; epochs by code: {epochs.events[:, 2].tolist().__len__()}")

    # Keep up to N epochs per class, spread evenly through the recording.
    selected = []
    code_to_label = {target[desc]: CLASS_CODES[int(desc)] for desc in target}
    for code, label in code_to_label.items():
        idx = np.flatnonzero(epochs.events[:, 2] == code)
        if len(idx) == 0:
            continue
        n_take = min(args.max_epochs_per_class, len(idx))
        chosen = np.unique(np.linspace(0, len(idx) - 1, n_take).round().astype(int))
        for local_idx in chosen:
            selected.append((label, epochs.get_data(copy=False)[idx[local_idx], 0, :]))
    if not selected:
        raise RuntimeError("No epochs found for left/right hand classes")

    rows = []
    ranges = [(0.01, 0.10), (0.02, 0.30), (0.05, 0.50)]
    for epoch_num, (label, signal) in enumerate(selected, start=1):
        signal = (signal - signal.mean()) / (signal.std() + 1e-12)
        for tau in [4, 5]:
            for m in [2, 3, 4, 5, 6, 8, 10]:
                for q_low, q_high in ranges:
                    slope, r2, nfit = slope_for_range(
                        signal, m=m, tau=tau, theiler=20,
                        q_low=q_low, q_high=q_high, n_radii=50,
                    )
                    rows.append({
                        "epoch_number": epoch_num, "class": label,
                        "channel": picks[0], "tau_samples": tau,
                        "embedding_dimension": m, "theiler_samples": 20,
                        "distance_quantile_low": q_low,
                        "distance_quantile_high": q_high,
                        "slope": slope, "r2": r2, "n_fit_points": nfit,
                    })
    df = pd.DataFrame(rows)
    epoch_csv = out_dir / "d2_epoch_sensitivity.csv"
    df.to_csv(epoch_csv, index=False)
    summary = (df.groupby(["class", "tau_samples", "embedding_dimension",
                           "distance_quantile_low", "distance_quantile_high"], dropna=False)
                 .agg(slope_median=("slope", "median"), slope_mean=("slope", "mean"),
                      r2_median=("r2", "median"), n_epochs=("epoch_number", "nunique"))
                 .reset_index())
    summary_csv = out_dir / "d2_summary.csv"
    summary.to_csv(summary_csv, index=False)
    pd.set_option("display.max_rows", 120)
    pd.set_option("display.width", 180)
    print("\nD2 PARAMETER SENSITIVITY SUMMARY — EXPLORATORY ONLY")
    print(summary.to_string(index=False, formatters={
        "slope_median": "{:.4f}".format, "slope_mean": "{:.4f}".format,
        "r2_median": "{:.4f}".format,
    }))
    print(f"\nSaved per-epoch results: {epoch_csv}")
    print(f"Saved summary:           {summary_csv}")
    print("Do not interpret a high R² as proof of a valid scaling plateau. Inspect radius-range and embedding-dimension stability.")


if __name__ == "__main__":
    main()
