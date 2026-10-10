#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
OUT_DIR = WORK_DIR


def find_step02_file(date: str) -> Path:
    p = WORK_DIR / "step02a_base_with_results_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step02 file not found: {p}")
    return p


def build_race_structure(date: str) -> pd.DataFrame:
    df = pd.read_csv(find_step02_file(date))

    required = ["date", "venue_id", "race_no", "car_no", "line_id", "line_pos"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns in step02: {missing}")

    for col in ["venue_id", "race_no", "car_no", "line_id", "line_pos"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    race_keys = ["date", "venue_id", "race_no"]

    line_size_df = (
        df.groupby(race_keys + ["line_id"], dropna=False)
        .size()
        .reset_index(name="line_size")
    )

    df = df.merge(
        line_size_df,
        on=race_keys + ["line_id"],
        how="left",
        validate="many_to_one",
    )

    race_line_summary = (
        line_size_df.groupby(race_keys)
        .agg(
            race_num_lines=("line_id", "nunique"),
            race_avg_line_size=("line_size", "mean"),
            race_std_line_size=("line_size", "std"),
            race_max_line_size=("line_size", "max"),
            race_num_solo=("line_size", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )

    race_racer_summary = (
        df.groupby(race_keys)
        .agg(
            race_num_racers=("car_no", "count"),
            race_leader_count=("line_pos", lambda s: int((s == 1).sum())),
        )
        .reset_index()
    )

    race_features = race_racer_summary.merge(
        race_line_summary,
        on=race_keys,
        how="left",
        validate="one_to_one",
    )

    out = df.merge(
        race_features,
        on=race_keys,
        how="left",
        validate="many_to_one",
    )

    out["line_is_solo"] = (out["line_size"] == 1).astype(int)
    out["line_is_leader"] = (out["line_pos"].fillna(-1) == 1).astype(int)
    out["line_is_second"] = (out["line_pos"].fillna(-1) == 2).astype(int)

    out["race_std_line_size"] = out["race_std_line_size"].fillna(0)

    out = out.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step03_race_structure START ==========")
    print(f"[INFO] date={args.date}")

    out = build_race_structure(args.date)
    latest_path = OUT_DIR / "step03_race_structure_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step03_race_structure rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step03_race_structure END ==========")


if __name__ == "__main__":
    main()
