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

from common import load_shmoo_data, build_grid, generate_make_targets, parse_args, METRIC_LABELS


def plot_xy(
    voltages_V: np.ndarray,
    freqs_MHz: np.ndarray,
    values: np.ndarray,
    correct: np.ndarray,
    metric: str,
    output: Path,
    title_suffix: str = "",
) -> None:
    """
    Plot frequency (x) vs metric (y).
    One colored marker-only series per voltage (no connecting lines).
    Only correct (non-NaN) points are plotted.
    """
    fig, ax = plt.subplots(figsize=(8, 8))

    for i, v in enumerate(voltages_V):
        row_vals = values[i, :]
        row_corr = correct[i, :]

        # Mask to keep only correct & non-NaN
        mask = ~np.isnan(row_vals) & row_corr
        if not np.any(mask):
            continue

        x = freqs_MHz[mask]
        y = row_vals[mask]

        # Marker-only, no connecting line, star markers
        ax.plot(
            x,
            y,
            marker="*",
            linestyle="None",
            label=f"{v:.2f} V",
        )

    ax.set_xlabel("Frequency [MHz]")

    pretty_metric = METRIC_LABELS.get(metric, metric)
    ax.set_ylabel(pretty_metric)

    if title_suffix:
        ax.set_title(f"{pretty_metric} vs Frequency ({title_suffix})")
    else:
        ax.set_title(f"{pretty_metric} vs Frequency")

    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.5)

    # Legend below the plot
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        legend = ax.legend(
            handles,
            labels,
            title="Core Voltage",
            loc="upper center",
            bbox_to_anchor=(0.5, -0.1),
            ncol=min(len(labels), 6),
        )
    else:
        legend = None

    # Leave some space at the bottom for the legend
    plt.tight_layout(rect=(0, 0, 1, 0.9))

    fig.savefig(output, format=output.suffix.lstrip("."), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()

    data = load_shmoo_data(args.json)
    voltages_V, freqs_MHz, grid_vals, grid_correct = build_grid(data, args.metric)

    if args.print_make_targets:
        generate_make_targets(voltages_V, freqs_MHz, grid_correct)

    plot_xy(
        voltages_V,
        freqs_MHz,
        grid_vals,
        grid_correct,
        metric=args.metric,
        output=args.output,
        title_suffix=args.title_suffix,
    )


if __name__ == "__main__":
    main()
