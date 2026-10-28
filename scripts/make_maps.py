"""Draw the sprint maps of fishing activity and infrastructure.

Outputs (in figures/):
  cables_in_danish_waters.png            needs data/external/dk.json and cable-geo.json
  positions_by_flag_<month>.png          one map per month with data

Defaults to all fishing vessels (data/processed/fishing_vessels_2024.csv,
created by prepare_data.py from the raw parquet file). Any processed CSV
can be passed instead, e.g. the Russian subset that ships with the repo.

Usage:
    python scripts/make_maps.py
    python scripts/make_maps.py --input data/processed/russian_fishing_vessels_2024.csv --months 7 9
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from _paths import ROOT
from illegal_maritime_activity import classify_mmsi, load_ais
from illegal_maritime_activity.plotting import (
    load_basemaps, plot_cables_in_danish_waters, plot_positions_by_flag,
)
from illegal_maritime_activity.preprocessing import TIMESTAMP


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path,
                        default=ROOT / "data" / "processed" / "fishing_vessels_2024.csv")
    parser.add_argument("--months", type=int, nargs="*",
                        help="months to map (default: every month with data)")
    parser.add_argument("--figures-dir", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    args.figures_dir.mkdir(exist_ok=True)

    waters, cables = load_basemaps()
    if waters is not None and cables is not None:
        fig, _ = plot_cables_in_danish_waters(waters, cables)
        fig.savefig(args.figures_dir / "cables_in_danish_waters.png", dpi=200)
        plt.close(fig)
    else:
        print("Skipping cable map: add dk.json and cable-geo.json to data/external/")

    if not args.input.exists():
        print(f"Skipping flag maps: {args.input} not found (run prepare_data.py first)")
        return

    df = load_ais(args.input)
    df["country"] = df["MMSI"].apply(classify_mmsi)
    months = args.months or sorted(df[TIMESTAMP].dt.month.unique())
    for month in months:
        fig, _ = plot_positions_by_flag(df, waters, cables, month=month)
        fig.savefig(args.figures_dir / f"positions_by_flag_{month:02d}.png", dpi=200)
        plt.close(fig)
    print(f"Saved {len(months)} monthly maps to {args.figures_dir}")


if __name__ == "__main__":
    main()
