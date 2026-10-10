#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
OUT_DIR = WORK_DIR

WINDOWS = [365, 180, 90]
SCOPES = ["all", "car9", "car7"]


def normalize_feature_base_types(df: pd.DataFrame) -> pd.DataFrame:
    """Minimal type normalization for feature_base master scripts."""
    out = df.copy()
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    int_cols = [
        "venue_id",
        "race_no",
        "car_no",
        "racer_id",
        "line_id",
        "line_pos",
        "line_size",
        "result_rank",
        "profile_area_group",
    ]
    for col in int_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    return out


def find_step05_file(date: str) -> Path:
    p = WORK_DIR / "step05_line_position_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step05 file not found: {p}")
    return p


def list_result_files(start_date: str, end_date: str) -> list[Path]:
    files = sorted(RESULTS_DIR.glob("**/results_*.csv"))
    selected = []
    for p in files:
        d = p.stem.replace("results_", "")
        if start_date <= d <= end_date:
            selected.append(p)
    return selected


def normalize_results_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "race_num": "race_no",
        "race_number": "race_no",
        "car_number": "car_no",
        "rank": "result_rank",
        "result": "result_rank",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def read_history_results(target_date: str) -> pd.DataFrame:
    target = pd.to_datetime(target_date)
    start = (target - pd.Timedelta(days=max(WINDOWS))).strftime("%Y-%m-%d")
    end = (target - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    files = list_result_files(start, end)
    if not files:
        raise FileNotFoundError(f"no results files found from {start} to {end}")

    frames = []
    for p in files:
        try:
            tmp = pd.read_csv(p)
            tmp = normalize_results_columns(tmp)
            frames.append(tmp)
        except Exception as e:
            print(f"[WARN] skip {p}: {e}")

    hist = pd.concat(frames, ignore_index=True)
    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist = hist[(hist["date"] >= pd.to_datetime(start)) & (hist["date"] <= pd.to_datetime(end))].copy()

    return hist


def add_basic_flags(hist: pd.DataFrame) -> pd.DataFrame:
    hist = hist.copy()

    hist["racer_id"] = pd.to_numeric(hist["racer_id"], errors="coerce").astype("Int64")
    hist["result_rank"] = pd.to_numeric(hist.get("result_rank"), errors="coerce")

    if "race_no" in hist.columns:
        hist["race_no"] = pd.to_numeric(hist["race_no"], errors="coerce")
    if "car_no" in hist.columns:
        hist["car_no"] = pd.to_numeric(hist["car_no"], errors="coerce")

    # 車数別レース判定用。results内で同一レースの出走数を数える。
    race_keys = ["date", "venue_id", "race_no"]
    if all(c in hist.columns for c in race_keys):
        racer_count = (
            hist.groupby(race_keys, dropna=False)
            .size()
            .reset_index(name="history_race_num_racers")
        )
        hist = hist.merge(racer_count, on=race_keys, how="left", validate="many_to_one")
    else:
        hist["history_race_num_racers"] = pd.NA

    hist["is_car9"] = (pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 9).astype(int)
    hist["is_car7"] = (pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 7).astype(int)

    hist["is_finish"] = hist["result_rank"].notna().astype(int)
    hist["is_win"] = (hist["result_rank"] == 1).astype(int)
    hist["is_second"] = (hist["result_rank"] == 2).astype(int)
    hist["is_third"] = (hist["result_rank"] == 3).astype(int)
    hist["is_top2"] = hist["result_rank"].between(1, 2).fillna(False).astype(int)
    hist["is_top3"] = hist["result_rank"].between(1, 3).fillna(False).astype(int)

    return hist[hist["racer_id"].notna()].copy()


def aggregate_one(hist: pd.DataFrame, target_date: str, window_days: int, scope: str) -> pd.DataFrame:
    target = pd.to_datetime(target_date)
    start = target - pd.Timedelta(days=window_days)
    end = target - pd.Timedelta(days=1)

    tmp = hist[(hist["date"] >= start) & (hist["date"] <= end)].copy()

    if scope == "car9":
        tmp = tmp[tmp["is_car9"] == 1].copy()
    elif scope == "car7":
        tmp = tmp[tmp["is_car7"] == 1].copy()

    suffix = f"{window_days}d_{scope}"

    g = tmp.groupby("racer_id", dropna=False)

    feat = g.agg(
        **{
            f"racer_race_count_{suffix}": ("is_finish", "sum"),
            f"racer_win_count_{suffix}": ("is_win", "sum"),
            f"racer_second_count_{suffix}": ("is_second", "sum"),
            f"racer_third_count_{suffix}": ("is_third", "sum"),
            f"racer_top2_count_{suffix}": ("is_top2", "sum"),
            f"racer_top3_count_{suffix}": ("is_top3", "sum"),
            f"racer_mean_rank_{suffix}": ("result_rank", "mean"),
        }
    ).reset_index()

    denom = feat[f"racer_race_count_{suffix}"].replace(0, pd.NA)

    feat[f"racer_win_rate_{suffix}"] = feat[f"racer_win_count_{suffix}"] / denom
    feat[f"racer_second_rate_{suffix}"] = feat[f"racer_second_count_{suffix}"] / denom
    feat[f"racer_third_rate_{suffix}"] = feat[f"racer_third_count_{suffix}"] / denom
    feat[f"racer_top2_rate_{suffix}"] = feat[f"racer_top2_count_{suffix}"] / denom
    feat[f"racer_top3_rate_{suffix}"] = feat[f"racer_top3_count_{suffix}"] / denom

    return feat


def build_window_features(hist: pd.DataFrame, target_date: str) -> pd.DataFrame:
    features = None

    for window_days in WINDOWS:
        for scope in SCOPES:
            one = aggregate_one(hist, target_date, window_days, scope)
            if features is None:
                features = one
            else:
                features = features.merge(one, on="racer_id", how="outer", validate="one_to_one")

    if features is None:
        raise RuntimeError("no features built")

    count_cols = [c for c in features.columns if "_count_" in c or "_race_count_" in c]
    rate_cols = [c for c in features.columns if "_rate_" in c]
    mean_cols = [c for c in features.columns if "_mean_" in c]

    for c in count_cols:
        features[c] = pd.to_numeric(features[c], errors="coerce").fillna(0).astype("Int64")
    for c in rate_cols:
        features[c] = pd.to_numeric(features[c], errors="coerce").fillna(0)
    for c in mean_cols:
        features[c] = pd.to_numeric(features[c], errors="coerce")

    return features


def build_step06(date: str) -> pd.DataFrame:
    base = pd.read_csv(find_step05_file(date))
    base = normalize_feature_base_types(base)

    hist = read_history_results(date)
    hist = add_basic_flags(hist)
    feat = build_window_features(hist, date)

    key_cols = ["date", "venue_id", "race_no", "car_no", "racer_id"]
    feature_cols = [c for c in feat.columns if c != "racer_id"]

    out = base[key_cols].merge(feat, on="racer_id", how="left", validate="many_to_one")
    out = out[key_cols + feature_cols]

    count_cols = [c for c in out.columns if "_count_" in c or "_race_count_" in c]
    rate_cols = [c for c in out.columns if "_rate_" in c]
    mean_cols = [c for c in out.columns if "_mean_" in c]

    for c in count_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).astype("Int64")
    for c in rate_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    for c in mean_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = normalize_feature_base_types(out)
    out = out.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step06_feature_racer_history_windows START ==========")
    print(f"[INFO] date={args.date}")

    out = build_step06(args.date)
    latest_path = OUT_DIR / "step06_feature_racer_history_windows_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step06_feature_racer_history_windows rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step06_feature_racer_history_windows END ==========")


if __name__ == "__main__":
    main()
