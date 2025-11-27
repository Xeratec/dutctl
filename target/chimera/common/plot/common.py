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

# Pretty labels for metrics
METRIC_LABELS = {
    "ops_per_cycle": "Op per Cycle",
    "ops_per_second": "MOp per Second",
    "power": "Power [mW]",
    "energy_efficiency": "Energy Efficiency [GOp/J]",
}


# ----------------- Data loading & processing ----------------- #

def _extract_power(meas_core_v: Dict[str, Any]) -> Optional[float]:
    """
    Extract power from the nested meas_core_V structure:
    {
      "E36312A_1": {
        "1": {
          "cur": ...,
          "vol": ...
        }
      }
    }
    We take the first device and the first channel.

    Returns power in Watts (A * V) or None if not available.
    """
    if not meas_core_v:
        return None

    try:
        device_dict = next(iter(meas_core_v.values()))
        channel_dict = next(iter(device_dict.values()))
        cur = channel_dict.get("cur")
        vol = channel_dict.get("vol")
    except StopIteration:
        return None

    if cur is None or vol is None:
        return None

    return cur * vol


def load_shmoo_data(json_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Read the JSON file and return a dictionary with the following keys
    for each datapoint:

    - correct
    - meas_ops_per_cycle
    - meas_ops_per_second
    - power
    - energy_efficiency
    - cfg_core_mV
    - cfg_fll_MHz

    Missing values are set to None.
    """
    with json_path.open("r") as f:
        raw = json.load(f)

    result: Dict[str, Dict[str, Any]] = {}


    for key, entry in raw.items():
        correct = bool(entry.get("correct", False))

        ops_per_cycle = entry.get("meas_ops_per_cycle")
        ops_per_second = entry.get("meas_ops_per_second")
        meas_core_v = entry.get("meas_core_V", {})
        power = _extract_power(meas_core_v) if meas_core_v else None

        if correct and ops_per_second is not None and power not in (None, 0):
            energy_eff = ops_per_second / power
        else:
            energy_eff = None

        result[key] = {
            "correct": correct,
            "ops_per_cycle": ops_per_cycle if correct else None,
            "ops_per_second": ops_per_second if correct else None,
            "power": power*1000 if correct and power is not None else None,
            "energy_efficiency": energy_eff/1000 if energy_eff is not None else None,
            "cfg_core_mV": entry.get("cfg_core_mV"),
            "cfg_fll_MHz": entry.get("cfg_fll_MHz"),
        }

        import pprint
        if entry.get("cfg_fll_MHz") == 425:
            print(f"Power {result[key]['power']} mW at {entry.get('cfg_core_mV')} mV and {entry.get('cfg_fll_MHz')} MHz")
            print(result[key])
    return result


def build_grid(
    data: Dict[str, Dict[str, Any]],
    metric: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build 2D grids (voltage x frequency) for the chosen metric.

    Returns:
      voltages_V: 1D array of unique voltages in V, sorted ascending
      freqs_MHz:  1D array of unique freqs in MHz, sorted ascending
      grid_vals:  2D array [len(voltages), len(freqs)] with metric values (float or nan)
      grid_correct: 2D boolean array for correctness
    """
    # Collect all voltages and freqs
    volts_mV: List[int] = []
    freqs_MHz: List[int] = []

    for entry in data.values():
        v = entry.get("cfg_core_mV")
        f = entry.get("cfg_fll_MHz")
        if v is not None and f is not None:
            volts_mV.append(v)
            freqs_MHz.append(f)


    unique_volts_mV = sorted(set(volts_mV))
    unique_freqs_MHz = sorted(set(freqs_MHz))

    voltages_V = np.array(unique_volts_mV, dtype=float) / 1000.0
    freqs_MHz_arr = np.array(unique_freqs_MHz, dtype=float)

    # Initialize grid with NaNs
    grid_vals = np.full(
        (len(unique_volts_mV), len(unique_freqs_MHz)), np.nan, dtype=float
    )
    grid_correct = np.zeros_like(grid_vals, dtype=bool)

    # Fill grid
    for entry in data.values():
        v_mV = entry.get("cfg_core_mV")
        f_MHz = entry.get("cfg_fll_MHz")
        if v_mV is None or f_MHz is None:
            continue

        try:
            i = unique_volts_mV.index(v_mV)
            j = unique_freqs_MHz.index(f_MHz)
        except ValueError:
            continue  # shouldn't happen, but be safe

        val = entry.get(metric)
        correct = bool(entry.get("correct", False))

        if correct and val is not None:
            grid_vals[i, j] = float(val)
        else:
            grid_vals[i, j] = np.nan

        grid_correct[i, j] = correct

    return voltages_V, freqs_MHz_arr, grid_vals, grid_correct


def generate_make_targets(voltages_V: np.ndarray, freqs_MHz: np.ndarray, grid_correct: np.ndarray) -> None:
    """
    For each voltage, print a make target listing failed measurements up to the
    highest correct frequency, and also print the first frequency above that
    highest correct one (if any) as a single measurement name.
    """
    for i, v in enumerate(voltages_V):
        row = grid_correct[i]
        # collect correct frequencies for this voltage
        correct_freqs = [f for k, f in enumerate(freqs_MHz) if row[k]]
        if correct_freqs:
            max_freq = max(correct_freqs)
            # failed frequencies smaller or equal to the highest correct frequency
            failed = [f for k, f in enumerate(freqs_MHz) if not row[k] and f <= max_freq]
            make_targets = []
            if failed:
                make_targets.extend(f"meas-{int(v*1000)}.{int(f)}" for f in failed)
            # first frequency greater than max_freq, if it exists
            next_freq = next((f for f in freqs_MHz if f > max_freq), None)
            if max_freq:
                make_targets.append(f"meas-{int(v*1000)}.{int(max_freq)}")
            if next_freq is not None:
                make_targets.append(f"meas-{int(v*1000)}.{int(next_freq)}")
            if make_targets:
                print(f"make {' '.join(make_targets)}")
        else:
            # no correct frequencies: nothing to do (original behaviour printed nothing)
            continue

# ----------------- Plotting ----------------- #

def plot_shmoo(
    voltages_V: np.ndarray,
    freqs_MHz: np.ndarray,
    values: np.ndarray,
    correct: np.ndarray,
    metric: str,
    output: Path,
    title_suffix: str = "",
) -> None:
    """
    Plot a single-panel shmoo plot (Voltage vs Frequency) colored by `values`.

    Incorrect or missing points are marked with a red 'X'.
    """
    masked_vals = np.ma.masked_invalid(values)

    fig, ax = plt.subplots(figsize=(10, 4))

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
    ax.set_xticks(np.arange(len(freqs_MHz)))
    ax.set_xticklabels([f"{int(f)}" for f in freqs_MHz], rotation=45, ha="right")
    ax.set_xlabel("Frequency [MHz]")

    ax.set_yticks(np.arange(len(voltages_V)))
    ax.set_yticklabels([f"{v:.2f} V" for v in voltages_V])
    ax.set_ylabel("Core Voltage [V]")

    pretty_metric = METRIC_LABELS.get(metric, metric)

    if title_suffix:
        ax.set_title(f"{pretty_metric} ({title_suffix})")
    else:
        ax.set_title(f"{pretty_metric}")

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
    cbar.set_label(pretty_metric)

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


# ----------------- CLI ----------------- #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a shmoo plot from JSON measurement data."
    )
    parser.add_argument(
        "json",
        type=Path,
        help="Path to input JSON file with measurement data.",
    )
    parser.add_argument(
        "-m",
        "--metric",
        choices=[
            "ops_per_cycle",
            "ops_per_second",
            "power",
            "energy_efficiency",
        ],
        default="energy_efficiency",
        help="Metric to plot on the shmoo heatmap.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("shmoo.svg"),
        help="Output image file (e.g., shmoo.svg, shmoo.png).",
    )
    parser.add_argument(
        "--title-suffix",
        type=str,
        default="",
        help="Optional suffix added to the plot title (e.g., benchmark name).",
    )
    parser.add_argument(
        "-p",
        "--print-make-targets",
        action="store_true",
        help="Print make targets for missing measurements.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data = load_shmoo_data(args.json)
    voltages_V, freqs_MHz, grid_vals, grid_correct = build_grid(data, args.metric)

    if args.print_make_targets:
        generate_make_targets(voltages_V, freqs_MHz, grid_correct)

    plot_shmoo(
        voltages_V,
        freqs_MHz,
        grid_vals,
        grid_correct,
        metric=args.metric,
        output=args.output,
        title_suffix=args.title_suffix,
    )


# ----------------- CLI ----------------- #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a shmoo plot from JSON measurement data."
    )
    parser.add_argument(
        "json",
        type=Path,
        help="Path to input JSON file with measurement data.",
    )
    parser.add_argument(
        "-m",
        "--metric",
        choices=[
            "ops_per_cycle",
            "ops_per_second",
            "power",
            "energy_efficiency",
        ],
        default="energy_efficiency",
        help="Metric to plot on the shmoo heatmap.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("shmoo.svg"),
        help="Output image file (e.g., shmoo.svg, shmoo.png).",
    )
    parser.add_argument(
        "--title-suffix",
        type=str,
        default="",
        help="Optional suffix added to the plot title (e.g., benchmark name).",
    )
    parser.add_argument(
        "-p",
        "--print-make-targets",
        action="store_true",
        help="Print make targets for missing measurements.",
    )
    return parser.parse_args()