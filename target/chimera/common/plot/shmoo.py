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

from common import load_data, infer_scales, build_grid, generate_make_targets, parse_args, METRIC_LABELS, METRIC_SCALES

def plot_shmoo(
    voltages: np.ndarray,
    freqs: np.ndarray,
    values: np.ndarray,
    correct: np.ndarray,
    metric: str,
    output: Path,
    v_scale: float,
    f_scale: float,
    m_scale: float,
    title_suffix: str = "",
) -> None:
    """
    Plot a single-panel shmoo plot (Voltage vs Frequency) colored by `values`.

    Incorrect or missing points are marked with a red 'X'.
    """
    masked_vals = np.ma.masked_invalid(values)

    fig, ax = plt.subplots(figsize=(10, 6))

    # colormap similar to the example: truncated plasma
    vmin = np.nanmin(values)
    vmax = np.nanmax(values)

    if np.isnan(vmin) or np.isnan(vmax):
        raise RuntimeError("All values are NaN – nothing to plot.")

    orig_cmap = plt.cm.plasma
    truncated_colors = orig_cmap(np.linspace(0.0, 0.9, 256))
    cmap = mcolors.LinearSegmentedColormap.from_list("plasma_trunc", truncated_colors)
    cmap.set_bad(color="#ffffff")

    im = ax.imshow(
        masked_vals,
        cmap=cmap,
        aspect="auto",
        vmin=vmin,
        vmax=vmax,
        origin="upper",
    )

    # Axes ticks/labels
    ax.set_xticks(np.arange(len(freqs)))
    ax.set_xticklabels([f"{int(f)}" for f in freqs], rotation=45, ha="right")
    ax.set_xlabel("Frequency " + f"{METRIC_SCALES[f_scale]}Hz")

    ax.set_yticks(np.arange(len(voltages)))
    ax.set_yticklabels([f"{v:.2f} {METRIC_SCALES[v_scale]}V" for v in voltages])
    ax.set_ylabel("Core Voltage " + f"{METRIC_SCALES[v_scale]}V")

    pretty_metric = METRIC_LABELS.get(metric, metric)
    unit = pretty_metric[0]
    if pretty_metric[1]:
        unit += f" [{METRIC_SCALES[m_scale]}{pretty_metric[1]}]"

    if title_suffix:
        ax.set_title(f"{unit} ({title_suffix})")
    else:
        ax.set_title(unit)

    # Overlay numbers / X marks
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            val = values[i, j]
            if np.isnan(val) or not correct[i, j]:
                ax.text(
                    j,
                    i,
                    "X",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="red",
                    fontweight="bold",
                )

    # Invert the y-axis to have low voltages at the bottom
    ax.invert_yaxis()

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(unit)

    # Label the lowest and highest values on the colorbar
    # calulcate number of decimals based on range
    range_val = vmax - vmin
    if range_val >= 100:
        decimals = 0
    elif range_val >= 10:
        decimals = 1
    elif range_val >= 1:
        decimals = 2
    else:
        decimals = 3

    cbar.ax.text(1, 1.02, f"{vmax:.{decimals}f}", transform=cbar.ax.transAxes, va="bottom", ha="center")
    cbar.ax.text(1, -0.02, f"{vmin:.{decimals}f}", transform=cbar.ax.transAxes, va="top", ha="center")

    plt.tight_layout()
    fig.savefig(output, format=output.suffix.lstrip("."), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()

    data = load_data(args.json)

    v_scale = 1
    f_scale = 1e-6
    m_scale = infer_scales(data, args.metric)

    voltages, freqs, grid_vals, grid_correct = build_grid(data, args.metric, v_scale=v_scale, f_scale=f_scale, metric_scale=m_scale)

    if args.print_make_targets > 0:
        generate_make_targets(voltages, freqs, grid_correct, args.print_make_targets)

    plot_shmoo(
        voltages,
        freqs,
        grid_vals,
        grid_correct,
        metric=args.metric,
        output=args.output,
        v_scale=v_scale,
        f_scale=f_scale,
        m_scale=m_scale,
        title_suffix=args.title_suffix,
    )


if __name__ == "__main__":
    main()
