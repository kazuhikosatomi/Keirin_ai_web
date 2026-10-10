#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
OUT_DIR = WORK_DIR

RECENT_WINDOWS = [5, 10]
SCOPES = ["all", "car9", "car7"]


def find_step06_file(date: str) -> Path:
    p = WORK_DIR / "step06_feature_racer_history_windows_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step06 file not found: {p}")
    return p


def list_result_files(target_date: str) -> list[Path]:
    target = pd.to_datetime(target_date)
    start = (target - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    end = (target - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    files = []
    for p in sorted(RESULTS_DIR.glob("**/results_*.csv")):
        d = p.stem.replace("results_", "")
        if start <= d <= end:
            files.append(p)
    return files


def normalize_results_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "race_num": "race_no",
        "race_number": "race_no",
        "car_number": "car_no",
        "rank": "result_rank",
        "result": "result_rank",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def form_score(rank: float) -> int:
    if pd.isna(rank):
        return 0
    if rank == 1:
        return 5
    if rank == 2:
        return 3
    if rank == 3:
        return 2
    return 0


def build_recent_features(target_date: str) -> pd.DataFrame:
    frames = []
    for p in list_result_files(target_date):
        tmp = pd.read_csv(p)
        tmp = normalize_results_columns(tmp)
        frames.append(tmp)

    if not frames:
        raise RuntimeError("no history results found")

    hist = pd.concat(frames, ignore_index=True)

    required = ["date", "venue_id", "race_no", "racer_id", "result_rank"]
    missing = [c for c in required if c not in hist.columns]
    if missing:
        raise ValueError(f"missing required columns in history results: {missing}")

    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist["venue_id"] = pd.to_numeric(hist["venue_id"], errors="coerce")
    hist["race_no"] = pd.to_numeric(hist["race_no"], errors="coerce")
    hist["racer_id"] = pd.to_numeric(hist["racer_id"], errors="coerce").astype("Int64")
    hist["result_rank"] = pd.to_numeric(hist["result_rank"], errors="coerce")

    # 車数別レース判定用。results内で同一レースの出走数を数える。
    race_keys = ["date", "venue_id", "race_no"]
    racer_count = (
        hist.groupby(race_keys, dropna=False)
        .size()
        .reset_index(name="history_race_num_racers")
    )
    hist = hist.merge(racer_count, on=race_keys, how="left", validate="many_to_one")
    hist["is_car9"] = (
        pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 9
    ).astype(int)
    hist["is_car7"] = (
        pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 7
    ).astype(int)

    def calc_recent(g: pd.DataFrame, n: int, scope: str) -> dict:
        if scope == "car9":
            g = g[g["is_car9"] == 1].copy()
        elif scope == "car7":
            g = g[g["is_car7"] == 1].copy()

        ranks = g[g["result_rank"].notna()].tail(n)["result_rank"].tolist()
        suffix = f"{n}_{scope}"

        return {
            f"racer_recent_race_count_{suffix}": len(ranks),
            f"racer_recent_mean_rank_{suffix}": sum(ranks) / len(ranks) if ranks else pd.NA,
            f"racer_recent_top2_count_{suffix}": sum(1 for r in ranks if r <= 2),
            f"racer_recent_top3_count_{suffix}": sum(1 for r in ranks if r <= 3),
            f"racer_recent_form_score_{suffix}": sum(form_score(r) for r in ranks),
        }

    rows = []
    for racer_id, g in hist.groupby("racer_id", dropna=False):
        row = {"racer_id": racer_id}
        for n in RECENT_WINDOWS:
            for scope in SCOPES:
                row.update(calc_recent(g, n, scope))
        rows.append(row)

    feat = pd.DataFrame(rows)

    int_cols = []
    for n in RECENT_WINDOWS:
        for scope in SCOPES:
            suffix = f"{n}_{scope}"
            int_cols.extend([
                f"racer_recent_race_count_{suffix}",
                f"racer_recent_top2_count_{suffix}",
                f"racer_recent_top3_count_{suffix}",
                f"racer_recent_form_score_{suffix}",
            ])
    for c in int_cols:
        if c in feat.columns:
            feat[c] = pd.to_numeric(feat[c], errors="coerce").fillna(0).astype("Int64")

    return feat


def build_step07(date: str) -> pd.DataFrame:
    base = pd.read_csv(find_step06_file(date))
    base["racer_id"] = pd.to_numeric(base["racer_id"], errors="coerce").astype("Int64")

    recent = build_recent_features(date)

    key_cols = ["date", "venue_id", "race_no", "car_no", "racer_id"]

    out = (
        base[key_cols]
        .merge(recent, on="racer_id", how="left", validate="many_to_one")
    )

    out = out.sort_values(
        ["date", "venue_id", "race_no", "car_no"]
    ).reset_index(drop=True)

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step07_feature_racer_recent START ==========")
    print(f"[INFO] date={args.date}")

    out = build_step07(args.date)
    latest_path = OUT_DIR / "step07_feature_racer_recent_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step07_feature_racer_recent rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step07_feature_racer_recent END ==========")


if __name__ == "__main__":
    main()
