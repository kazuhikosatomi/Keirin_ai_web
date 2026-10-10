#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
OUT_DIR = WORK_DIR


def find_step04_file(date: str) -> Path:
    p = WORK_DIR / "step04_area_features_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step04 file not found: {p}")
    return p


def build_line_position(date: str) -> pd.DataFrame:
    df = pd.read_csv(find_step04_file(date))

    required = ["date", "venue_id", "race_no", "car_no", "line_id", "line_pos", "line_size"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns in step04: {missing}")

    for col in ["venue_id", "race_no", "car_no", "line_id", "line_pos", "line_size"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["line_pos_ratio"] = df["line_pos"] / df["line_size"]
    df["line_distance_from_tail"] = df["line_size"] - df["line_pos"]

    df["line_is_leader"] = (df["line_pos"] == 1).astype(int)
    df["line_is_tail"] = (df["line_pos"] == df["line_size"]).astype(int)
    df["line_is_third_or_later"] = (df["line_pos"] >= 3).astype(int)
    df["line_is_middle"] = (
        (df["line_pos"] > 1) & (df["line_pos"] < df["line_size"])
    ).astype(int)

    df["line_is_second"] = (df["line_pos"] == 2).astype(int)

    for int_col in ["result_rank", "profile_area_group"]:
        if int_col in df.columns:
            df[int_col] = pd.to_numeric(df[int_col], errors="coerce").astype("Int64")

    df = df.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step05_line_position START ==========")
    print(f"[INFO] date={args.date}")

    out = build_line_position(args.date)
    latest_path = OUT_DIR / "step05_line_position_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step05_line_position rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step05_line_position END ==========")


if __name__ == "__main__":
    main()
