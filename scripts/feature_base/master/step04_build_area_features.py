#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
MASTER_PATH = PROJECT_ROOT / "data" / "master" / "prefectures_master.csv"
OUT_DIR = WORK_DIR


def find_step03_file(date: str) -> Path:
    p = WORK_DIR / "step03_race_structure_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step03 file not found: {p}")
    return p


def normalize_prefecture_name(value: object) -> str:
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if not s:
        return ""

    alias_map = {
        "北海": "北海道",
        "神奈": "神奈川",
        "京都": "京都府",
        "和歌": "和歌山",
        "鹿児": "鹿児島",
    }
    s = alias_map.get(s, s)

    for suffix in ["都", "道", "府", "県"]:
        if s.endswith(suffix):
            return s[:-1]
    return s


def build_area_features(date: str) -> pd.DataFrame:
    df = pd.read_csv(find_step03_file(date))
    master = pd.read_csv(MASTER_PATH)

    master = master.rename(columns={
        "prefecture": "master_prefecture",
        "area": "profile_area",
        "group": "profile_area_group",
    })

    df["prefecture_key"] = df["profile_prefecture"].apply(normalize_prefecture_name)
    master["prefecture_key"] = master["master_prefecture"].apply(normalize_prefecture_name)

    df = df.merge(
        master[["prefecture_key", "profile_area", "profile_area_group"]],
        on="prefecture_key",
        how="left",
        validate="many_to_one",
    )

    df = df.drop(columns=["prefecture_key"])

    df["profile_area_group"] = pd.to_numeric(
        df["profile_area_group"], errors="coerce"
    ).astype("Int64")

    keys_race = ["date", "venue_id", "race_no"]
    keys_line = ["date", "venue_id", "race_no", "line_id"]

    line_area = (
        df.groupby(keys_line, dropna=False)
        .agg(
            line_num_areas=("profile_area", "nunique"),
            line_num_area_groups=("profile_area_group", "nunique"),
        )
        .reset_index()
    )
    line_area["line_has_cross_area"] = (line_area["line_num_areas"] >= 2).astype(int)
    line_area["line_has_cross_group"] = (line_area["line_num_area_groups"] >= 2).astype(int)

    df = df.merge(line_area, on=keys_line, how="left", validate="many_to_one")

    race_area = (
        df.groupby(keys_race, dropna=False)
        .agg(
            race_num_areas=("profile_area", "nunique"),
            race_num_area_groups=("profile_area_group", "nunique"),
            race_has_cross_area_line=("line_has_cross_area", "max"),
            race_has_cross_group_line=("line_has_cross_group", "max"),
        )
        .reset_index()
    )

    df = df.merge(race_area, on=keys_race, how="left", validate="many_to_one")

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
    print("========== feature_base master / step04_area_features START ==========")
    print(f"[INFO] date={args.date}")

    out = build_area_features(args.date)
    latest_path = OUT_DIR / "step04_area_features_latest.csv"

    out.to_csv(latest_path, index=False)

    area_missing = out["profile_area"].isna().sum() if "profile_area" in out.columns else 0

    print(f"[OK] step04_area_features rows={len(out)} cols={len(out.columns)}")
    print(f"[INFO] profile_area_missing={area_missing}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step04_area_features END ==========")


if __name__ == "__main__":
    main()
