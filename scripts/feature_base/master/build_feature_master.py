#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
FINAL_DIR = PROJECT_ROOT / "data" / "feature_base" / "master"

KEY_COLS = ["date", "venue_id", "race_no", "car_no", "racer_id"]
RACE_KEY_COLS = ["date", "venue_id", "race_no"]

BASE_KEEP_COLS = [
    "date",
    "venue_id",
    "venue_name",
    "race_no",
    "cup_name",
    "cup_day",
    "race_grade",
    "result_rank",
    "result_status",
    "result_status_raw",
    "result_label",
    "result_finish_tactic",
    "result_margin",
    "car_no",
    "racer_id",
    "racer_name",
    "profile_prefecture",
    "profile_class_name",
    "profile_class_grade",
    "profile_age",
    "profile_term",
    "racer_score",
    "line_id",
    "line_pos",
    "line_is_seri",
    "line_seri_order",
    "line_has_seri",
    "line_size",
    "line_pos_ratio",
    "line_distance_from_tail",
    "line_is_second",
    "line_is_middle",
    "line_is_tail",
    "line_is_solo",
    "line_is_leader",
    "line_is_third_or_later",
    "race_num_racers",
    "race_num_lines",
    "race_num_solo",
    "race_avg_line_size",
    "race_std_line_size",
    "race_max_line_size",
    "race_leader_count",
    "profile_area",
    "profile_area_group",
    "line_num_areas",
    "line_num_area_groups",
    "line_has_cross_area",
    "line_has_cross_group",
    "race_num_areas",
    "race_num_area_groups",
    "race_has_cross_area_line",
    "race_has_cross_group_line",
    "entry_recent_s_count",
    "entry_recent_h_count",
    "entry_recent_b_count",
]

FEATURE_INPUTS = [
    ("step06", "step06_feature_racer_history_windows_latest.csv"),
    ("step07", "step07_feature_racer_recent_latest.csv"),
    ("step08", "step08_feature_line_strength_latest.csv"),
    ("step09", "step09_feature_racer_tactic_latest.csv"),
    ("step10", "step10_feature_racer_shb_latest.csv"),
]

RACE_FEATURE_INPUTS = [
    ("step11", "step11_feature_race_summary_latest.csv"),
]


def path_for_step05(date: str) -> Path:
    return WORK_DIR / "step05_line_position_latest.csv"


def path_for_feature(step_name: str, filename: str, date: str) -> Path:
    return WORK_DIR / filename


def normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    for col in ["venue_id", "race_no", "car_no", "racer_id"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out


def read_base(date: str) -> pd.DataFrame:
    p = path_for_step05(date)
    if not p.exists():
        raise FileNotFoundError(f"step05 base file not found: {p}")

    df = pd.read_csv(p)
    df = normalize_keys(df)

    keep = [c for c in BASE_KEEP_COLS if c in df.columns]
    missing = [c for c in KEY_COLS if c not in keep]
    if missing:
        raise ValueError(f"base missing key columns: {missing}")

    out = df[keep].copy()
    if out.duplicated(KEY_COLS).any():
        raise ValueError("base has duplicated KEY_COLS")

    return out


def read_feature(date: str, step_name: str, filename: str) -> pd.DataFrame:
    p = path_for_feature(step_name, filename, date)
    if not p.exists():
        raise FileNotFoundError(f"feature file not found: {p}")

    df = pd.read_csv(p)
    df = normalize_keys(df)

    missing = [c for c in KEY_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{p.name} missing key columns: {missing}")

    if df.duplicated(KEY_COLS).any():
        raise ValueError(f"{p.name} has duplicated KEY_COLS")

    return df


def read_race_feature(
    date: str,
    step_name: str,
    filename: str,
) -> pd.DataFrame:
    p = path_for_feature(
        step_name,
        filename,
        date,
    )

    if not p.exists():
        raise FileNotFoundError(
            f"race feature file not found: {p}"
        )

    df = pd.read_csv(p)
    df = normalize_keys(df)

    missing = [
        column
        for column in RACE_KEY_COLS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{p.name} missing race key columns: {missing}"
        )

    if df.duplicated(RACE_KEY_COLS).any():
        raise ValueError(
            f"{p.name} has duplicated RACE_KEY_COLS"
        )

    return df


def build_feature_master(date: str) -> pd.DataFrame:
    out = read_base(date)

    for step_name, filename in FEATURE_INPUTS:
        feat = read_feature(date, step_name, filename)

        # line_has_seri は Step05 の正式ライン情報を保持する。
        # Step08 にも同名列があるが、Step05 と同値であり、
        # Step08 側は集約特徴量の計算用なので merge 対象から除外する。
        if step_name == "step08" and "line_has_seri" in feat.columns:
            feat = feat.drop(columns=["line_has_seri"])

        before_cols = len(out.columns)

        overlap = sorted((set(out.columns) & set(feat.columns)) - set(KEY_COLS))
        if overlap:
            raise ValueError(f"column overlap detected in {filename}: {overlap[:20]}")

        out = out.merge(feat, on=KEY_COLS, how="left", validate="one_to_one")

        print(
            f"[INFO] merged {step_name}: "
            f"rows={len(out)} cols={before_cols}->{len(out.columns)}"
        )

    for step_name, filename in RACE_FEATURE_INPUTS:
        feat = read_race_feature(
            date,
            step_name,
            filename,
        )

        before_cols = len(out.columns)

        overlap = sorted(
            (
                set(out.columns)
                & set(feat.columns)
            )
            - set(RACE_KEY_COLS)
        )

        if overlap:
            raise ValueError(
                f"column overlap detected in {filename}: "
                f"{overlap[:20]}"
            )

        out = out.merge(
            feat,
            on=RACE_KEY_COLS,
            how="left",
            validate="many_to_one",
        )

        print(
            f"[INFO] merged {step_name}: "
            f"rows={len(out)} "
            f"cols={before_cols}->{len(out.columns)}"
        )

    out = out.sort_values(
        [
            "date",
            "venue_id",
            "race_no",
            "car_no",
        ]
    ).reset_index(drop=True)

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--mode",
        choices=["train", "predict"],
        default="train",
        help="output mode: train=結果あり学習用, predict=結果なし予測用",
    )
    args = parser.parse_args()

    mode_dir = FINAL_DIR / args.mode
    mode_dir.mkdir(parents=True, exist_ok=True)

    print("========== feature_base master / build_feature_master START ==========")
    print(f"[INFO] date={args.date}")
    print(f"[INFO] mode={args.mode}")

    out = build_feature_master(args.date)

    year_dir = mode_dir / args.date[:4]
    year_dir.mkdir(parents=True, exist_ok=True)

    out_path = year_dir / f"feature_base_{args.mode}_{args.date}.csv"
    latest_path = mode_dir / f"feature_base_{args.mode}_latest.csv"

    out.to_csv(out_path, index=False)
    out.to_csv(latest_path, index=False)

    print(f"[OK] feature_base rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {out_path}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / build_feature_master END ==========")


if __name__ == "__main__":
    main()
