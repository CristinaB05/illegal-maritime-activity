"""Build the processed datasets from the raw AIS parquet file.

Steps:
  1. keep only fishing vessels and tag each vessel with its flag group;
  2. save all fishing vessels, then the subset for one flag group.

The raw file (aisdk-2024-30m.parquet) is not tracked because of its size.

Usage:
    python scripts/prepare_data.py data/raw/aisdk-2024-30m.parquet --flag Russian
"""

import argparse
from pathlib import Path

from _paths import ROOT
from illegal_maritime_activity import classify_mmsi, filter_fishing, filter_flag, load_ais


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("parquet", type=Path, help="raw AIS parquet file")
    parser.add_argument("--flag", default="Russian", choices=["Russian", "Danish", "FoC"],
                        help="flag group to extract (default: Russian)")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fishing = filter_fishing(load_ais(args.parquet))
    fishing["country"] = fishing["MMSI"].apply(classify_mmsi)

    # All fishing vessels: input for the flag comparison maps.
    all_path = args.out_dir / "fishing_vessels_2024.csv"
    fishing.to_csv(all_path)
    print(f"{len(fishing):,} fishing-vessel messages -> {all_path}")

    # One flag group: input for the dark-period analysis.
    subset = filter_flag(fishing, args.flag).drop(columns="country")
    flag_path = args.out_dir / f"{args.flag.lower()}_fishing_vessels_2024.csv"
    subset.to_csv(flag_path)
    print(f"{len(subset):,} messages from {subset['MMSI'].nunique()} vessels -> {flag_path}")


if __name__ == "__main__":
    main()
