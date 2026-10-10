#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"

IN_PATH = OUT_DIR / "step01_base_latest.csv"
OUT_PATH = OUT_DIR / "step02b_predict_base_latest.csv"

RESULT_COLS = [
    "result_rank",
    "result_status",
    "result_label",
    "result_finish_tactic",
    "result_margin",
    "result_payoff_2t",
    "result_payoff_3t",
]


def build_step02b(date: str) -> pd.DataFrame:
    if not IN_PATH.exists():
        raise FileNotFoundError(
            f"{IN_PATH}\n"
            "先に step01_build_base.py を実行してください。"
        )

    base = pd.read_csv(IN_PATH, dtype=str)

    if "date" not in base.columns:
        raise KeyError("step01_base_latest.csv に date 列がありません")

    base = base[base["date"].astype(str) == str(date)].copy()

    for col in RESULT_COLS:
        if col not in base.columns:
            base[col] = pd.NA

    # 予測用なので結果はまだ存在しない。後続処理で扱いやすいように明示する。
    base["result_status"] = "PREDICT"
    base["result_label"] = pd.NA

    if "result_rank" in base.columns:
        base["result_rank"] = pd.to_numeric(base["result_rank"], errors="coerce")

    # 後続stepの期待に合わせて、学習用step02と同じ主要列順へ寄せる
    preferred = [
        "date",
        "venue_id",
        "venue_name",
        "race_no",
        "grade",
        "cup_name",
        "cup_day",
        "post_time",
        "car_no",
        "racer_id",
        "racer_name",
        "prefecture",
        "grade_id",
        "age",
        "term",
        "tactics",
        "S",
        "B",
        "H",
        "line_id",
        "line_pos",
        "line_is_seri",
        "line_seri_order",
        "line_has_seri",
        "line_size",
        "result_rank",
        "result_status",
        "result_label",
        "result_finish_tactic",
        "result_margin",
        "result_payoff_2t",
        "result_payoff_3t",
    ]

    cols = [c for c in preferred if c in base.columns]
    rest = [c for c in base.columns if c not in cols]
    out = base[cols + rest].copy()

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    print("========== feature_base master / step02b_predict_base START ==========")
    print(f"[INFO] date={args.date}")

    out = build_step02b(args.date)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)

    print(f"[OK] step02b_predict_base rows={len(out)} cols={len(out.columns)}")
    print(f"[INFO] result_status_counts={out['result_status'].value_counts(dropna=False).to_dict() if 'result_status' in out.columns else {}}")
    print(f"[OK] saved -> {OUT_PATH}")
    print("========== feature_base master / step02b_predict_base END ==========")


if __name__ == "__main__":
    main()
