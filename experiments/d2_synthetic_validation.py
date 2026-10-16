"""Exploratory correlation-dimension diagnostics on synthetic signals.

Run from any directory:
    python experiments/d2_synthetic_validation.py

This script is a numerical sanity check, not a proof that D2 is correctly
identified for arbitrary signals. It reports sensitivity to radius ranges.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import linregress

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "d2_synthetic"


def make_signals(n: int = 1200, fs: float = 250.0, seed: int = 2026):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fs
    sine = np.sin(2 * np.pi * 10 * t)
    noisy_sine = sine + 0.25 * rng.normal(size=n)
    two_frequency = np.sin(2 * np.pi * 8 * t) + 0.7 * np.sin(2 * np.pi * 17 * t)
    white_noise = rng.normal(size=n)
    return {
        "sine": sine,
        "noisy_sine": noisy_sine,
        "two_frequency": two_frequency,
        "white_noise": white_noise,
    }


def delay_embedding(x: np.ndarray, m: int, tau: int) -> np.ndarray:
    n_vectors = len(x) - (m - 1) * tau
    if n_vectors < 100:
        raise ValueError("Not enough samples for this embedding dimension and delay")
    return np.column_stack([x[j * tau:j * tau + n_vectors] for j in range(m)])


def correlation_curve(x: np.ndarray, m: int, tau: int, theiler: int = 20,
                      n_radii: int = 50):
    emb = delay_embedding(x, m, tau)
    n = len(emb)
    i, j = np.triu_indices(n, k=theiler + 1)
    distance_matrix = cdist(emb, emb, metric="euclidean")
    distances = distance_matrix[i, j]
    distances = distances[np.isfinite(distances) & (distances > 0)]
    if len(distances) < 100:
        raise ValueError("Too few valid pairwise distances")
    radii = np.unique(np.geomspace(np.quantile(distances, 0.01),
                                   np.quantile(distances, 0.60), n_radii))
    corr = np.array([(distances < r).mean() for r in radii])
    keep = corr > 0
    return radii[keep], corr[keep]


def fit_range(radii: np.ndarray, corr: np.ndarray, q_low: float, q_high: float):
    # Radius quantiles are computed on the radii grid to compare scale ranges.
    lo, hi = np.quantile(radii, [q_low, q_high])
    use = (radii >= lo) & (radii <= hi) & (corr > 0)
    if use.sum() < 6:
        return np.nan, np.nan, int(use.sum())
    fit = linregress(np.log(radii[use]), np.log(corr[use]))
    return float(fit.slope), float(fit.rvalue ** 2), int(use.sum())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    tau = 4
    theiler = 20
    ranges = [(0.05, 0.35), (0.10, 0.55), (0.15, 0.70)]
    for signal_name, signal in make_signals().items():
        signal = (signal - signal.mean()) / (signal.std() + 1e-12)
        for m in [2, 3, 4, 5, 6, 8, 10]:
            radii, corr = correlation_curve(signal, m, tau, theiler=theiler)
            for q_low, q_high in ranges:
                slope, r2, n_fit = fit_range(radii, corr, q_low, q_high)
                rows.append({
                    "signal": signal_name, "m": m, "tau": tau,
                    "theiler": theiler, "radius_grid_q_low": q_low,
                    "radius_grid_q_high": q_high, "slope": slope,
                    "r2": r2, "n_fit_points": n_fit,
                })
    df = pd.DataFrame(rows)
    output_csv = OUT / "synthetic_d2_sensitivity.csv"
    df.to_csv(output_csv, index=False)
    pd.set_option("display.max_rows", 100)
    pd.set_option("display.width", 160)
    print("\nSYNTHETIC D2 SENSITIVITY — EXPLORATORY DIAGNOSTIC")
    print(f"Settings: tau={tau}, Theiler={theiler}; radius ranges refer to quantiles of the generated radius grid.")
    print(df.to_string(index=False, formatters={"slope": "{:.4f}".format, "r2": "{:.4f}".format}))
    print(f"\nSaved: {output_csv}")
    print("Interpretation warning: a high R² alone does not prove a valid scaling region.")


if __name__ == "__main__":
    main()
