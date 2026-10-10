#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STEP01_PATH = (
    PROJECT_ROOT
    / "data"
    / "feature_base"
    / "work"
    / "step01_base_latest.csv"
)

WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
OUT_DIR = WORK_DIR

KEY_COLS = ["date", "venue_id", "race_no", "car_no", "racer_id"]
LINE_KEYS = ["date", "venue_id", "race_no", "line_id"]


def find_step05_file(date: str) -> Path:
    p = WORK_DIR / "step05_line_position_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step05 file not found: {p}")
    return p


def find_step06_file(date: str) -> Path:
    p = WORK_DIR / "step06_feature_racer_history_windows_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step06 file not found: {p}")
    return p


def find_step07_file(date: str) -> Path:
    p = WORK_DIR / "step07_feature_racer_recent_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step07 file not found: {p}")
    return p



def attach_entry_recent_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Step08入力に含まれない当日のS・H・B回数を、
    Step01基礎出力から選手キーで追加する。
    """

    entry_columns = [
        "entry_recent_s_count",
        "entry_recent_h_count",
        "entry_recent_b_count",
    ]

    if all(
        column in df.columns
        for column in entry_columns
    ):
        return df

    if not STEP01_PATH.exists():
        raise FileNotFoundError(
            f"step01出力がありません: {STEP01_PATH}"
        )

    base = pd.read_csv(
        STEP01_PATH,
        usecols=[
            *KEY_COLS,
            *entry_columns,
        ],
        low_memory=False,
    )

    if base.duplicated(KEY_COLS).any():
        raise ValueError(
            "step01_base_latest.csvに"
            "KEY_COLS重複があります"
        )

    duplicate_entry_columns = [
        column
        for column in entry_columns
        if column in df.columns
    ]

    if duplicate_entry_columns:
        df = df.drop(
            columns=duplicate_entry_columns
        )

    out = df.merge(
        base,
        on=KEY_COLS,
        how="left",
        validate="one_to_one",
    )

    missing_counts = (
        out[entry_columns]
        .isna()
        .sum()
    )

    if missing_counts.any():
        raise ValueError(
            "Step01から結合したentry_recent列に"
            "欠損があります:\n"
            + missing_counts.to_string()
        )

    return out


def build_line_strength(date: str) -> pd.DataFrame:
    base = pd.read_csv(find_step05_file(date))
    feat06 = pd.read_csv(find_step06_file(date))
    feat07 = pd.read_csv(find_step07_file(date))

    required = KEY_COLS + ["line_id", "line_pos", "racer_score"]

    optional_line_cols = [c for c in ["line_is_seri", "line_has_seri"] if c in base.columns]
    df = base[KEY_COLS + ["line_id", "line_pos", "racer_score"] + optional_line_cols].copy()

    for col in ["venue_id", "race_no", "car_no", "racer_id", "line_id", "line_pos"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["line_is_seri", "line_has_seri"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("Int64")
    df["racer_score"] = pd.to_numeric(df["racer_score"], errors="coerce")

    # 内部計算用に、選手の履歴特徴量・直近特徴量を一時的に結合する。
    # 出力にはKEY_COLS + step08固有featureだけを残す。
    feat06 = feat06.copy()
    feat07 = feat07.copy()
    for tmp in [feat06, feat07]:
        tmp["date"] = pd.to_datetime(tmp["date"]).dt.strftime("%Y-%m-%d")
        for col in ["venue_id", "race_no", "car_no", "racer_id"]:
            if col in tmp.columns:
                tmp[col] = pd.to_numeric(tmp[col], errors="coerce").astype("Int64")

    df = df.merge(feat06, on=KEY_COLS, how="left", validate="one_to_one")
    df = df.merge(feat07, on=KEY_COLS, how="left", validate="one_to_one")

    windows = ["365d", "180d", "90d"]
    targets = ["all", "car9", "car7"]

    history_rate_cols = []
    for window in windows:
        for target in targets:
            history_rate_cols.extend([
                f"racer_win_rate_{window}_{target}",
                f"racer_top2_rate_{window}_{target}",
                f"racer_top3_rate_{window}_{target}",
            ])

    recent_score_cols = [
        "racer_recent_form_score_5_all",
        "racer_recent_form_score_10_all",
        "racer_recent_form_score_5_car9",
        "racer_recent_form_score_10_car9",
        "racer_recent_form_score_5_car7",
        "racer_recent_form_score_10_car7",
    ]

    numeric_candidates = history_rate_cols + recent_score_cols

    for col in numeric_candidates:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    line_base_aggs = {
        "line_score_mean": ("racer_score", "mean"),
        "line_score_std": ("racer_score", "std"),
        "line_second_count": ("line_pos", lambda s: int((s == 2).sum())),
        "line_seri_count": ("line_is_seri", "sum") if "line_is_seri" in df.columns else ("line_pos", lambda s: 0),
        "line_has_seri": ("line_has_seri", "max") if "line_has_seri" in df.columns else ("line_pos", lambda s: 0),
    }

    for window in windows:
        for target in targets:
            win_col = f"racer_win_rate_{window}_{target}"
            top2_col = f"racer_top2_rate_{window}_{target}"
            top3_col = f"racer_top3_rate_{window}_{target}"
            if win_col in df.columns:
                line_base_aggs[f"line_avg_win_rate_{window}_{target}"] = (win_col, "mean")
            if top2_col in df.columns:
                line_base_aggs[f"line_avg_top2_rate_{window}_{target}"] = (top2_col, "mean")
            if top3_col in df.columns:
                line_base_aggs[f"line_avg_top3_rate_{window}_{target}"] = (top3_col, "mean")

    for col in recent_score_cols:
        if col in df.columns:
            out_col = col.replace("racer_recent_", "line_avg_recent_")
            line_base_aggs[out_col] = (col, "mean")

    line_base = (
        df.groupby(LINE_KEYS, dropna=False)
        .agg(**line_base_aggs)
        .reset_index()
    )

    leader_source_cols = ["racer_score"] + [c for c in history_rate_cols + recent_score_cols if c in df.columns]
    leaders = df[df["line_pos"] == 1][LINE_KEYS + leader_source_cols].copy()

    leader_rename = {"racer_score": "line_leader_score"}
    for col in history_rate_cols:
        if col in leaders.columns:
            leader_rename[col] = col.replace("racer_", "line_leader_", 1)
    for col in recent_score_cols:
        if col in leaders.columns:
            leader_rename[col] = col.replace("racer_recent_", "line_leader_recent_", 1)
    leaders = leaders.rename(columns=leader_rename)

    second_source_cols = ["racer_score"] + [c for c in history_rate_cols + recent_score_cols if c in df.columns]
    seconds = (
        df[df["line_pos"] == 2][LINE_KEYS + second_source_cols]
        .groupby(LINE_KEYS, dropna=False)
        .mean(numeric_only=True)
        .reset_index()
    )

    second_rename = {"racer_score": "line_second_score"}
    for col in history_rate_cols:
        if col in seconds.columns:
            second_rename[col] = col.replace("racer_", "line_second_", 1)
    for col in recent_score_cols:
        if col in seconds.columns:
            second_rename[col] = col.replace("racer_recent_", "line_second_recent_", 1)
    seconds = seconds.rename(columns=second_rename)

    line_feat = line_base.merge(leaders, on=LINE_KEYS, how="left", validate="one_to_one")
    line_feat = line_feat.merge(seconds, on=LINE_KEYS, how="left", validate="one_to_one")

    line_feat["line_score_std"] = line_feat["line_score_std"].fillna(0)

    df = attach_entry_recent_columns(df)

    line_has_rider = add_line_has_rider_features(
        df
    )[
        KEY_COLS
        + [
            "line_has_s_rider",
            "line_has_h_rider",
            "line_has_b_rider",
        ]
    ].copy()

    if line_has_rider.duplicated(KEY_COLS).any():
        raise ValueError(
            "line_has_riderにKEY_COLS重複があります"
        )

    out = df[KEY_COLS + ["line_id"]].merge(
        line_feat,
        on=LINE_KEYS,
        how="left",
        validate="many_to_one",
    )

    out = out.merge(
        line_has_rider,
        on=KEY_COLS,
        how="left",
        validate="one_to_one",
    )

    feature_cols = [
        column
        for column in out.columns
        if column not in KEY_COLS
        and column != "line_id"
    ]

    out = out[
        KEY_COLS
        + feature_cols
    ]

    out = out.sort_values(
        [
            "date",
            "venue_id",
            "race_no",
            "car_no",
        ]
    ).reset_index(
        drop=True
    )

    return out



def add_line_has_rider_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    当日の出走表に掲載された直近S・H・B回数を使用し、
    同一ライン内に該当選手が1人以上いるかを表す。

    line_has_s_rider:
        entry_recent_s_count > 0 の選手がライン内にいる

    line_has_h_rider:
        entry_recent_h_count > 0 の選手がライン内にいる

    line_has_b_rider:
        entry_recent_b_count > 0 の選手がライン内にいる
    """

    required_columns = [
        "date",
        "venue_id",
        "race_no",
        "line_id",
        "entry_recent_s_count",
        "entry_recent_h_count",
        "entry_recent_b_count",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "line_has_rider生成に必要な列がありません: "
            f"{missing_columns}"
        )

    out = df.copy()

    source_map = {
        "line_has_s_rider": "entry_recent_s_count",
        "line_has_h_rider": "entry_recent_h_count",
        "line_has_b_rider": "entry_recent_b_count",
    }

    line_keys = [
        "date",
        "venue_id",
        "race_no",
        "line_id",
    ]

    for output_column, source_column in source_map.items():
        numeric = pd.to_numeric(
            out[source_column],
            errors="coerce",
        ).fillna(0)

        rider_flag = numeric.gt(0).astype(int)

        out[output_column] = (
            rider_flag.groupby(
                [
                    out[column]
                    for column in line_keys
                ],
                dropna=False,
                sort=False,
            )
            .transform("max")
            .astype(int)
        )

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step08_feature_line_strength START ==========")
    print(f"[INFO] date={args.date}")

    out = build_line_strength(args.date)
    latest_path = OUT_DIR / "step08_feature_line_strength_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step08_feature_line_strength rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step08_feature_line_strength END ==========")


if __name__ == "__main__":
    main()
