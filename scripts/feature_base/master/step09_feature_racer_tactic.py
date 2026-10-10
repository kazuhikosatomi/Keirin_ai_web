#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
OUT_DIR = WORK_DIR

KEY_COLS = ["date", "venue_id", "race_no", "car_no", "racer_id"]
LINE_KEYS = ["date", "venue_id", "race_no", "line_id"]
WINDOWS = [365, 180, 90]
SCOPES = ["all", "car9", "car7"]
TACTICS = {
    "nige": "逃",
    "makuri": "捲",
    "sashi": "差",
    "ma": "マ",
}


def find_step05_file(date: str) -> Path:
    p = WORK_DIR / "step05_line_position_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"step05 file not found: {p}")
    return p


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "race_num": "race_no",
        "race_number": "race_no",
        "car_number": "car_no",
        "rank": "result_rank",
        "result": "result_rank",
        "finish_tactics": "result_finish_tactic",
        "finish_tactic": "result_finish_tactic",
        "tactics": "result_finish_tactic",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def list_history_files(base_dir: Path, prefix: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> list[Path]:
    if not base_dir.exists():
        return []

    files = []
    for p in base_dir.rglob(f"{prefix}_*.csv"):
        date_text = p.stem.replace(f"{prefix}_", "")
        try:
            d = pd.to_datetime(date_text)
        except Exception:
            continue
        if start_date <= d < end_date:
            files.append(p)
    return sorted(files)


def read_history_results(target_date: str) -> pd.DataFrame:
    end = pd.to_datetime(target_date)
    start = end - pd.Timedelta(days=max(WINDOWS))
    files = list_history_files(RESULTS_DIR, "results", start, end)
    if not files:
        raise FileNotFoundError(f"history results files not found: {start.date()} to {end.date()}")

    frames = []
    for p in files:
        df = pd.read_csv(p)
        df = normalize_columns(df)
        need = ["date", "venue_id", "race_no", "car_no", "racer_id", "result_rank"]
        if not set(need).issubset(df.columns):
            continue
        if "result_finish_tactic" not in df.columns:
            df["result_finish_tactic"] = ""
        keep = need + ["result_finish_tactic"]
        frames.append(df[keep].copy())

    if not frames:
        raise ValueError("usable history results rows not found")

    hist = pd.concat(frames, ignore_index=True)
    hist["date"] = pd.to_datetime(hist["date"]).dt.strftime("%Y-%m-%d")
    for col in ["venue_id", "race_no", "car_no", "racer_id"]:
        hist[col] = pd.to_numeric(hist[col], errors="coerce").astype("Int64")
    hist["result_rank"] = pd.to_numeric(hist["result_rank"], errors="coerce")

    # 同一レース・同一選手が複数resultsファイルから
    # 重複して読み込まれる場合がある。
    # 車数判定の前に1選手1行へ正規化する。
    history_racer_keys = [
        "date",
        "venue_id",
        "race_no",
        "car_no",
        "racer_id",
    ]

    before_dedup = len(hist)

    hist = hist.drop_duplicates(
        subset=history_racer_keys,
        keep="last",
    ).copy()

    removed_duplicates = (
        before_dedup
        - len(hist)
    )

    if removed_duplicates:
        print(
            "[INFO] history duplicate rows removed: "
            f"{removed_duplicates:,}"
        )

    race_keys = ["date", "venue_id", "race_no"]

    # 重複除去後の実選手行数から7車/9車を復元する。
    racer_count = (
        hist.groupby(
            race_keys,
            dropna=False,
        )
        .size()
        .reset_index(
            name="history_race_num_racers"
        )
    )
    hist = hist.merge(racer_count, on=race_keys, how="left", validate="many_to_one")
    hist["is_car9"] = (pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 9).astype(int)
    hist["is_car7"] = (pd.to_numeric(hist["history_race_num_racers"], errors="coerce") == 7).astype(int)
    return hist


def build_history(target_date: str) -> pd.DataFrame:
    hist = read_history_results(target_date)

    tactic = hist["result_finish_tactic"].astype(str).fillna("")
    for key, label in TACTICS.items():
        hist[f"tactic_{key}"] = tactic.str.contains(label).astype(int)

    hist = hist[hist["racer_id"].notna()].copy()
    hist = hist.sort_values(["racer_id", "date", "venue_id", "race_no", "car_no"])
    return hist


def aggregate_one(hist: pd.DataFrame, target_date: str, window_days: int, scope: str) -> pd.DataFrame:
    end = pd.to_datetime(target_date)
    start = end - pd.Timedelta(days=window_days)
    suffix = f"{window_days}d_{scope}"

    h = hist[(pd.to_datetime(hist["date"]) >= start) & (pd.to_datetime(hist["date"]) < end)].copy()
    if scope == "car9":
        h = h[h["is_car9"] == 1].copy()
    elif scope == "car7":
        h = h[h["is_car7"] == 1].copy()

    if h.empty:
        return pd.DataFrame(columns=["racer_id"])

    agg_dict = {
        f"racer_style_race_count_{suffix}": ("result_rank", "count"),
    }
    output_keys = {k: ("mark" if k == "ma" else k) for k in TACTICS}

    for key in TACTICS:
        out_key = output_keys[key]
        agg_dict[f"racer_tactic_{out_key}_count_{suffix}"] = (f"tactic_{key}", "sum")

    feat = h.groupby("racer_id", dropna=False).agg(**agg_dict).reset_index()

    denom = feat[f"racer_style_race_count_{suffix}"].replace(0, pd.NA)
    for key in TACTICS:
        out_key = output_keys[key]
        feat[f"racer_tactic_{out_key}_rate_{suffix}"] = (
            feat[f"racer_tactic_{out_key}_count_{suffix}"] / denom
        )

    return feat


def build_racer_style_feature(date: str) -> pd.DataFrame:
    current = pd.read_csv(find_step05_file(date))
    required = KEY_COLS + ["line_id", "line_pos"]
    missing = [c for c in required if c not in current.columns]
    if missing:
        raise ValueError(f"missing required columns in step05: {missing}")

    current = current[KEY_COLS + ["line_id", "line_pos"]].copy()
    for col in ["venue_id", "race_no", "car_no", "racer_id", "line_id", "line_pos"]:
        current[col] = pd.to_numeric(current[col], errors="coerce").astype("Int64")

    hist = build_history(date)

    feat = None
    for window in WINDOWS:
        for scope in SCOPES:
            part = aggregate_one(hist, date, window, scope)
            feat = part if feat is None else feat.merge(part, on="racer_id", how="outer", validate="one_to_one")

    if feat is None:
        feat = pd.DataFrame({"racer_id": pd.Series(dtype="Int64")})

    out = current.merge(feat, on="racer_id", how="left", validate="many_to_one")

    leaders = current[current["line_pos"] == 1][KEY_COLS + ["line_id"]].copy()
    leader_feat = leaders.merge(feat, on="racer_id", how="left", validate="many_to_one")

    rename = {}
    for c in leader_feat.columns:
        if c.startswith("racer_tactic_"):
            rename[c] = c.replace("racer_tactic_", "line_leader_tactic_")
        elif c.startswith("racer_style_race_count_"):
            rename[c] = c.replace("racer_style_race_count_", "line_leader_style_race_count_")
    leader_feat = leader_feat.rename(columns=rename)

    leader_feature_cols = [c for c in leader_feat.columns if c.startswith("line_leader_")]
    leader_feat = leader_feat[["date", "venue_id", "race_no", "line_id"] + leader_feature_cols].drop_duplicates(
        ["date", "venue_id", "race_no", "line_id"],
        keep="first",
    )

    out = out.merge(
        leader_feat,
        on=["date", "venue_id", "race_no", "line_id"],
        how="left",
        validate="many_to_one",
    )

    feature_cols = [c for c in out.columns if c not in KEY_COLS and c not in ["line_id", "line_pos"]]
    out = out[KEY_COLS + feature_cols]
    out = out.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("========== feature_base master / step09_feature_racer_tactic START ==========")
    print(f"[INFO] date={args.date}")

    out = build_racer_style_feature(args.date)
    latest_path = OUT_DIR / "step09_feature_racer_tactic_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step09_feature_racer_tactic rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step09_feature_racer_tactic END ==========")


if __name__ == "__main__":
    main()
