"""LOSO comparison of PSD and HFD features on BCI IV 2a training GDF files.

Expected files: data/raw/A01T.gdf ... data/raw/A09T.gdf
Run from project root:
    python experiments/classification_comparison.py --data-dir data/raw

The script computes features from 4-s cue-locked epochs after 4-40 Hz filtering.
It compares PSD band-power, HFD, and concatenated PSD+HFD features using the
same LOSO folds and an SVM. Results are exploratory until checked against the
exact final protocol and all available labeled files.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import warnings
import numpy as np
import pandas as pd
import mne
from antropy import higuchi_fd
from scipy.signal import welch
from scipy.integrate import trapezoid
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import balanced_accuracy_score, f1_score, confusion_matrix

MNE_LOG_LEVEL = "ERROR"
CLASS_CODES = {769: 0, 770: 1, 771: 2, 772: 3}
CLASS_NAMES = ["left_hand", "right_hand", "feet", "tongue"]
BANDS = {"theta": (4.0, 8.0), "alpha": (8.0, 13.0),
         "beta": (13.0, 30.0), "gamma": (30.0, 40.0)}


def parse_subject(path: Path) -> str:
    match = re.search(r"A(\d{2})T\.gdf$", path.name, flags=re.IGNORECASE)
    if not match:
        return path.stem
    return f"A{match.group(1)}"


def read_epochs(path: Path):
    raw = mne.io.read_raw_gdf(str(path), preload=True, verbose=MNE_LOG_LEVEL)
    events, mapping = mne.events_from_annotations(raw, verbose=MNE_LOG_LEVEL)
    selected_event_id = {}
    for description, code in mapping.items():
        key = str(description).strip()
        if key.isdigit() and int(key) in CLASS_CODES:
            selected_event_id[key] = int(code)
    if len(selected_event_id) < 2:
        raise RuntimeError(f"Could not identify class markers 769-772 in {path.name}: {mapping}")

    eeg_channels = [name for name, kind in zip(raw.ch_names, raw.get_channel_types())
                    if kind == "eeg" and not name.upper().startswith("EOG")]
    if not eeg_channels:
        # Backup for files whose channel types are not correctly identified by reader.
        eeg_channels = [name for name in raw.ch_names if "EOG" not in name.upper()]
    raw.filter(4.0, 40.0, picks=eeg_channels, verbose=MNE_LOG_LEVEL)
    sfreq = float(raw.info["sfreq"])
    epochs = mne.Epochs(raw, events, event_id=selected_event_id,
                        tmin=0.0, tmax=4.0 - 1.0 / sfreq,
                        baseline=None, preload=True, picks=eeg_channels,
                        reject_by_annotation=True, verbose=MNE_LOG_LEVEL)
    data = epochs.get_data(copy=False)
    # Translate the GDF marker numbers to the stable integer class order.
    marker_to_label = {selected_event_id[desc]: CLASS_CODES[int(desc)] for desc in selected_event_id}
    labels = np.array([marker_to_label[int(code)] for code in epochs.events[:, 2]], dtype=int)
    return data, labels, eeg_channels, sfreq


def extract_features(data: np.ndarray, sfreq: float, kmax: int):
    """Return HFD features, PSD band-power features, and stable feature names."""
    n_epochs, n_channels, _ = data.shape
    hfd = np.empty((n_epochs, n_channels), dtype=float)
    psd = np.empty((n_epochs, n_channels * len(BANDS)), dtype=float)
    hfd_names = [f"HFD_{ch + 1:02d}" for ch in range(n_channels)]
    psd_names = [f"{band}_{ch + 1:02d}" for ch in range(n_channels) for band in BANDS]
    for i in range(n_epochs):
        for ch in range(n_channels):
            signal = data[i, ch, :]
            hfd[i, ch] = higuchi_fd(signal, kmax=kmax)
            freqs, power = welch(signal, fs=sfreq, nperseg=min(512, len(signal)))
            for band_index, (band, (low, high)) in enumerate(BANDS.items()):
                idx = (freqs >= low) & (freqs < high)
                value = trapezoid(power[idx], freqs[idx]) if idx.sum() >= 2 else 0.0
                psd[i, ch * len(BANDS) + band_index] = value
    return hfd, psd, hfd_names, psd_names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw", help="Folder containing A01T.gdf ... A09T.gdf")
    parser.add_argument("--out", default=None, help="CSV output path; defaults to results/classification_loso.csv")
    parser.add_argument("--kmax", type=int, default=10, help="HFD maximum scale; default 10")
    args = parser.parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    files = sorted(data_dir.glob("A??T.gdf"))
    if not files:
        raise FileNotFoundError(f"No files matching A??T.gdf found in {data_dir}")
    if len(files) < 2:
        raise RuntimeError("LOSO evaluation requires at least two participant files")

    subjects = []
    X_hfd_parts, X_psd_parts, y_parts, group_parts = [], [], [], []
    print(f"Data directory: {data_dir}")
    print(f"Files found: {len(files)}")
    for path in files:
        subject = parse_subject(path)
        print(f"\n[{subject}] reading {path.name}")
        epochs, labels, channels, sfreq = read_epochs(path)
        hfd, psd, hfd_names, psd_names = extract_features(epochs, sfreq, args.kmax)
        X_hfd_parts.append(hfd)
        X_psd_parts.append(psd)
        y_parts.append(labels)
        group_parts.append(np.repeat(subject, len(labels)))
        subjects.append(subject)
        counts = {CLASS_NAMES[c]: int(np.sum(labels == c)) for c in range(4)}
        print(f"  epochs={len(labels)}, channels={len(channels)}, sfreq={sfreq:g} Hz, classes={counts}")

    X_hfd = np.vstack(X_hfd_parts)
    X_psd = np.vstack(X_psd_parts)
    y = np.concatenate(y_parts)
    groups = np.concatenate(group_parts)
    feature_sets = {
        "HFD": X_hfd,
        "PSD": X_psd,
        "PSD+HFD": np.hstack([X_psd, X_hfd]),
    }
    rows = []
    predictions = {name: np.full_like(y, fill_value=-1) for name in feature_sets}
    for test_subject in subjects:
        test = groups == test_subject
        train = ~test
        if np.unique(y[train]).size < 2 or np.unique(y[test]).size < 2:
            warnings.warn(f"Unexpected class coverage in fold {test_subject}")
        print(f"\nLOSO fold: test={test_subject}, train epochs={train.sum()}, test epochs={test.sum()}")
        for name, X in feature_sets.items():
            model = make_pipeline(StandardScaler(),
                                  SVC(kernel="rbf", class_weight="balanced", random_state=42))
            model.fit(X[train], y[train])
            pred = model.predict(X[test])
            predictions[name][test] = pred
            ba = balanced_accuracy_score(y[test], pred)
            f1 = f1_score(y[test], pred, average="macro", zero_division=0)
            rows.append({"feature_set": name, "test_subject": test_subject,
                         "n_train": int(train.sum()), "n_test": int(test.sum()),
                         "balanced_accuracy": ba, "macro_f1": f1})
            print(f"  {name:7s} balanced_accuracy={ba:.4f} macro_F1={f1:.4f}")

    fold_df = pd.DataFrame(rows)
    output_path = Path(args.out).expanduser().resolve() if args.out else Path(__file__).resolve().parents[1] / "results" / "classification_loso.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fold_df.to_csv(output_path, index=False)
    print("\nSUMMARY ACROSS LOSO FOLDS (mean ± standard deviation)")
    summary = fold_df.groupby("feature_set").agg(
        balanced_accuracy_mean=("balanced_accuracy", "mean"),
        balanced_accuracy_sd=("balanced_accuracy", "std"),
        macro_f1_mean=("macro_f1", "mean"), macro_f1_sd=("macro_f1", "std"),
    ).reset_index()
    print(summary.to_string(index=False, formatters={
        "balanced_accuracy_mean": "{:.4f}".format,
        "balanced_accuracy_sd": "{:.4f}".format,
        "macro_f1_mean": "{:.4f}".format,
        "macro_f1_sd": "{:.4f}".format,
    }))
    print("\nAggregated confusion matrices (rows=true, columns=predicted; labels 0-3 = left/right/feet/tongue)")
    for name in feature_sets:
        cm = confusion_matrix(y, predictions[name], labels=[0, 1, 2, 3])
        print(f"\n{name}\n{cm}")
    print(f"\nSaved fold-level results: {output_path}")
    print("Note: this is a reproducible baseline experiment, not a guarantee of publication-ready performance.")


if __name__ == "__main__":
    main()
