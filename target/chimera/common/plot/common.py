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

from typing import Tuple, Literal

# Pretty labels for metrics
METRIC_LABELS = {
    "ops_per_cycle": ["Op per Cycle", ""],
    "ops_per_second": ["Op per Second", "Op/s"],
    "power": ["Power", "W"],
    "energy_efficiency": ["Energy Efficiency", "Op/J"],
    "runtime_cycles": ["Runtime", "cycles"],
}

METRIC_SCALES = {
    1: "",
    1e-3: "k",
    1e-6: "M",
    1e-9: "G",
    1e-12: "T",
    1e3: "m",
    1e6: "µ",
    1e9: "n",
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


def load_data(json_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Read the JSON file and return a dictionary with the following keys
    for each datapoint:

    - correct
    - meas_ops_per_cycle
    - meas_runtime_cycles
    - meas_ops_per_second (MOp/s)
    - power (mW)
    - energy_efficiency (MOp/J)
    - cfg_core_mV
    - cfg_fll_MHz

    Missing values are set to None.
    """
    with json_path.open("r") as f:
        raw = json.load(f)

    result: Dict[str, Dict[str, Any]] = {}


    for key, entry in sorted(raw.items()):
        correct = bool(entry.get("correct", False))

        ops_per_cycle = entry.get("meas_ops_per_cycle")
        ops_per_second = entry.get("meas_ops_per_second")
        runtime_cycles = entry.get("meas_runtime_cycles")
        meas_core_v = entry.get("meas_core_V", {})
        cfg_core_mV = entry.get("cfg_core_mV")
        cfg_fll_MHz = entry.get("cfg_fll_MHz")
        power = _extract_power(meas_core_v) if meas_core_v else None

        if correct and ops_per_second is not None and power not in (None, 0):
            energy_eff = ops_per_second*1E6 / power
        else:
            energy_eff = None

        result[key] = {
            "correct": correct,
            "ops_per_cycle": ops_per_cycle if correct else None,
            "ops_per_second": ops_per_second*1E6 if correct else None,
            "runtime_cycles": runtime_cycles if correct else None,
            "power": power if correct and power is not None else None,
            "energy_efficiency": energy_eff if energy_eff is not None else None,
            "cfg_core": cfg_core_mV * 1E-3 if cfg_core_mV is not None else None,
            "cfg_fll": cfg_fll_MHz * 1E6 if cfg_fll_MHz is not None else None,
        }

    df = pd.DataFrame.from_dict(result, orient="index")
    return df


def infer_scales(df: pd.DataFrame, metric: str) -> float:
    """
    Infer an appropriate metric scale based on the maximum value in the DataFrame.
    """
    max_metric = df[metric].max()
    if pd.isna(max_metric) or max_metric == 0:
        return 1.0
    elif max_metric >= 1e13:
        return 1e-12
    elif max_metric >= 1e10:
        return 1e-9
    elif max_metric >= 1e7:
        return 1e-6
    elif max_metric >= 1e4:
        return 1e-3
    elif max_metric >= 1e1:
        return 1.0
    elif max_metric < 1:
        return 1e3
    elif max_metric < 1e-3:
        return 1e6
    elif max_metric < 1e-6:
        return 1e9
    else:
        return 1.0

def build_grid(
    df: pd.DataFrame,
    metric: str,
    *,
    v_scale: float = 1,          # multiply cfg_core by this for output axis (e.g. 1e3 -> mV)
    f_scale: float = 1e-6,          # multiply cfg_fll by this for output axis (e.g. 1e-6 -> MHz)
    metric_scale: float = 1.0,     # multiply metric by this (e.g. 1e-9 -> GOps/J if df is Ops/J)
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build 2D grids (voltage x frequency) for the chosen metric from a DataFrame,
    with optional scaling applied in the OUTPUT.

    Expected df columns (base units, no scaling):
      - cfg_core : voltage in V
      - cfg_fll  : frequency in Hz
      - correct  : bool
      - <metric> : metric in base units (e.g., Ops/J)

    Scaling:
      - output voltage axis uses cfg_core * v_scale
      - output freq axis uses cfg_fll * f_scale
      - grid metric uses metric * metric_scale

    Returns:
      voltages_out: 1D array of unique voltages (scaled), sorted ascending
      freqs_out:    1D array of unique freqs (scaled), sorted ascending
      grid_vals:    2D array [len(voltages), len(freqs)] with scaled metric values
      grid_correct: 2D boolean array for correctness
    """
    use = df[["cfg_core", "cfg_fll", "correct", metric]].copy()
    use["cfg_core"] = pd.to_numeric(use["cfg_core"], errors="coerce")
    use["cfg_fll"] = pd.to_numeric(use["cfg_fll"], errors="coerce")
    use[metric] = pd.to_numeric(use[metric], errors="coerce")
    use["correct"] = use["correct"].astype(bool)

    # Apply scaling for output
    use["v_out"] = use["cfg_core"] * v_scale
    use["f_out"] = use["cfg_fll"] * f_scale
    use["m_out"] = use[metric] * metric_scale

    # Unique axes
    unique_volts = np.array(sorted(use["v_out"].dropna().unique()), dtype=float)
    unique_freqs = np.array(sorted(use["f_out"].dropna().unique()), dtype=float)

    grid_vals = np.full((len(unique_volts), len(unique_freqs)), np.nan, dtype=float)
    grid_correct = np.zeros_like(grid_vals, dtype=bool)

    v_to_i = {v: i for i, v in enumerate(unique_volts)}
    f_to_j = {f: j for j, f in enumerate(unique_freqs)}

    # Fill grid (if duplicates exist, later rows overwrite earlier ones)
    for v, f, correct, val in use[["v_out", "f_out", "correct", "m_out"]].itertuples(index=False, name=None):
        if pd.isna(v) or pd.isna(f):
            continue

        i = v_to_i[float(v)]
        j = f_to_j[float(f)]

        grid_correct[i, j] = bool(correct)
        grid_vals[i, j] = float(val) if (correct and pd.notna(val)) else np.nan

    return unique_volts, unique_freqs, grid_vals, grid_correct


def generate_make_targets(voltages_V: np.ndarray, freqs_MHz: np.ndarray, grid_correct: np.ndarray, print_level: int) -> None:
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
            if print_level > 1:
                if max_freq:
                    make_targets.append(f"meas-{int(v*1000)}.{int(max_freq)}")
                if next_freq is not None:
                    make_targets.append(f"meas-{int(v*1000)}.{int(next_freq)}")
            if make_targets:
                print(f"make {' '.join(make_targets)}")
        else:
            # no correct frequencies: nothing to do (original behaviour printed nothing)
            continue

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
        action="count",
        default=0,
        help="Print make targets for missing measurements.",
    )
    return parser.parse_args()