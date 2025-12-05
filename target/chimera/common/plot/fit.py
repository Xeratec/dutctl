#! /usr/bin/env python3

# SPDX-FileCopyrightText: 2025 ETH Zurich and University of Bologna
# SPDX-License-Identifier: Apache-2.0

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd

from common import load_data, build_grid, generate_make_targets, parse_args, METRIC_LABELS

def fit_energy_efficiency_per_voltage(
    df: pd.DataFrame,
    current_A: float,
    ncycles: float,
    operations: float,
    alpha: float | None = None,
    C_F: float | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fits, for each voltage V, eta(f) = operations*f / (b + k*f^2),
    where b = V*current*ncycles and k is fitted (k = ncycles*alpha*C*V^2).

    Returns:
      fits_df: one row per voltage with fitted params and derived values
      preds_df: per-point predictions and residuals for each (V,f)
    """
    if (alpha is None) and (C_F is None):
        # It's still fine: we can fit k, but cannot split alpha vs C.
        pass

    # Convert frequency to Hz for physical consistency (optional but recommended)
    # If you want to keep MHz, it still "fits" but k units change accordingly.
    df = df.copy()
    df["freq_Hz"] = df["freq_MHz"] * 1e6

    fits = []
    preds = []

    def model_eta(f_Hz, k):
        # b is voltage-dependent; we'll close over b per-voltage by redefining model in loop.
        raise RuntimeError("This should be replaced inside the voltage loop.")

    for V, g in df.groupby("voltage_V", sort=True):
        f = g["freq_Hz"].to_numpy(dtype=float)
        y = g["energy_efficiency"].to_numpy(dtype=float)

        if len(f) < 2:
            # Not enough points to fit; still record NA
            fits.append(
                {
                    "voltage_V": V,
                    "k_fit": np.nan,
                    "k_fit_stderr": np.nan,
                    "alpha_implied_if_C_given": np.nan,
                    "C_implied_if_alpha_given": np.nan,
                    "rmse": np.nan,
                    "r2": np.nan,
                    "n_points": len(f),
                }
            )
            continue

        b = V * current_A * ncycles  # as requested

        # Define per-voltage model (only k is free)
        def eta_of_f(f_Hz, k):
            return (operations * f_Hz) / (b + k * (f_Hz**2))

        # Initial guess: small positive k; keep it non-negative (physical)
        p0 = [1e-18]
        bounds = (0.0, np.inf)

        popt, pcov = curve_fit(
            eta_of_f,
            f,
            y,
            p0=p0,
            bounds=bounds,
            maxfev=20000,
        )
        k_fit = float(popt[0])
        k_stderr = float(math.sqrt(pcov[0, 0])) if np.isfinite(pcov[0, 0]) else np.nan

        yhat = eta_of_f(f, k_fit)
        resid = y - yhat

        rmse = float(np.sqrt(np.mean(resid**2)))
        ss_res = float(np.sum(resid**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else np.nan

        # “All possible values” derivations from k = ncycles*alpha*C*V^2
        alpha_implied = np.nan
        C_implied = np.nan
        if C_F is not None and C_F > 0:
            alpha_implied = k_fit / (ncycles * C_F * (V**2))
        if alpha is not None and alpha > 0:
            C_implied = k_fit / (ncycles * alpha * (V**2))

        fits.append(
            {
                "voltage_V": V,
                "k_fit": k_fit,
                "k_fit_stderr": k_stderr,
                "alpha_implied_if_C_given": alpha_implied,
                "C_implied_if_alpha_given": C_implied,
                "rmse": rmse,
                "r2": r2,
                "n_points": int(len(f)),
                "b_static_VI_ncycles": b,
            }
        )

        # Per-point predictions
        tmp = g[["voltage_V", "freq_MHz", "freq_Hz", "energy_efficiency"]].copy()
        tmp["eta_pred"] = yhat
        tmp["residual"] = resid
        tmp["k_fit"] = k_fit
        preds.append(tmp)

    fits_df = pd.DataFrame(fits).sort_values("voltage_V").reset_index(drop=True)
    preds_df = pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()

    return fits_df, preds_df


def main():
    args = parse_args()

    df = load_data(args.json)
    df.to_csv(args.output, index=False)


    # # Provide the constants you need (from your experiment setup):
    # current_A = 0.02
    # ncycles = 1_000_000
    # operations = 123456789

    # # If you know one of these, you can get the other from the fit:
    # alpha = None     # e.g. 1.0
    # C_F = None       # e.g. 2.5e-9

    # fits_df, preds_df = fit_energy_efficiency_per_voltage(
    #     df,
    #     current_A=current_A,
    #     ncycles=ncycles,
    #     operations=operations,
    #     alpha=alpha,
    #     C_F=C_F,
    # )

if __name__ == "__main__":
    main()
