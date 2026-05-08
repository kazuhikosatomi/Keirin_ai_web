

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step04_merge_odds.py

目的:
step43 の買い目CSVに、既存のオッズCSVを結合する。

入力:
- data/sim06/step43/sim06_step43_all_top_tickets_YYYY-MM-DD.csv
- data/grade01/odds/YYYY/grade01_odds_YYYY-MM-DD.csv があれば優先
- なければ既存の data/odds/YYYY/odds_YYYY-MM-DD.csv などを読む

出力:
- data/grade01/step04/grade01_step04_tickets_with_odds_YYYY-MM-DD.csv

対象券種:
- 2車単: bet_code=3 / ticket_type=exacta
- 3連単: bet_code=5 / ticket_type=trifecta
- 3連複: bet_code=6 / ticket_type=trio
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_DATE = "2026-04-26"
OUT_DIR = Path("data/grade01/step04")

BET_CODE_TO_TYPE = {
    3: "exacta",
    5: "trifecta",
    6: "trio",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--odds-path", default=None, help="オッズCSVを明示指定する場合")
    return parser.parse_args()


def find_step43_path(date: str) -> Path:
    path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def find_odds_path(date: str, explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    year = date[:4]
    candidates = [
        # grade01専用の当日HP用オッズを最優先
        Path(f"data/grade01/odds/{year}/grade01_odds_{date}.csv"),
        Path(f"data/grade01/odds/grade01_odds_{date}.csv"),
        # 既存の過去分析・通常処理用オッズはフォールバック
        Path(f"data/odds/{year}/odds_{date}.csv"),
        Path(f"data/odds/odds_{date}.csv"),
        Path(f"data/odds_{date}.csv"),
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        "odds csv not found. tried: " + ", ".join(str(p) for p in candidates)
    )


def parse_race_id(race_id: str):
    # 例: 2026-04-26_42_04R
    parts = str(race_id).split("_")
    date = parts[0]
    venue_id = int(parts[1])
    race_no = int(parts[2].replace("R", ""))
    return date, venue_id, race_no


def normalize_step43(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "race_id" not in out.columns:
        raise ValueError("step43 missing race_id")
    if "ticket_key" not in out.columns:
        raise ValueError("step43 missing ticket_key")
    if "ticket_type" not in out.columns:
        raise ValueError("step43 missing ticket_type")

    parsed = out["race_id"].astype(str).map(parse_race_id)
    out["date"] = [x[0] for x in parsed]
    out["venue_id"] = [x[1] for x in parsed]
    out["race_no"] = [x[2] for x in parsed]
    out["ticket_key"] = out["ticket_key"].astype(str)
    out["ticket_type"] = out["ticket_type"].astype(str)

    return out


def to_int_str(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text == "":
        return ""
    try:
        return str(int(float(text)))
    except Exception:
        return text


def build_odds_ticket_key(row: pd.Series) -> str:
    bet_code = int(row["bet_code"])
    c1 = to_int_str(row.get("car_1"))
    c2 = to_int_str(row.get("car_2"))
    c3 = to_int_str(row.get("car_3"))

    if bet_code == 3:
        return f"{c1}-{c2}"
    if bet_code == 5:
        return f"{c1}-{c2}-{c3}"
    if bet_code == 6:
        cars = sorted([c for c in [c1, c2, c3] if c], key=lambda x: int(x))
        return "-".join(cars)
    return ""


def normalize_odds(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    out = df.copy()

    required = ["venue_id", "race_no", "bet_code", "car_1", "car_2", "odds_1"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"odds missing columns: {missing}")

    if "date" not in out.columns:
        out["date"] = target_date

    out["date"] = out["date"].astype(str)
    out["venue_id"] = pd.to_numeric(out["venue_id"], errors="coerce").astype("Int64")
    out["race_no"] = pd.to_numeric(out["race_no"], errors="coerce").astype("Int64")
    out["bet_code"] = pd.to_numeric(out["bet_code"], errors="coerce").astype("Int64")

    out = out[out["bet_code"].isin(list(BET_CODE_TO_TYPE.keys()))].copy()
    out["ticket_type"] = out["bet_code"].astype(int).map(BET_CODE_TO_TYPE)
    out["ticket_key"] = out.apply(build_odds_ticket_key, axis=1)

    out["final_odds"] = pd.to_numeric(out["odds_1"], errors="coerce")
    out["final_payout"] = (out["final_odds"] * 100).round(0)

    keep_cols = [
        "date",
        "venue_id",
        "race_no",
        "ticket_type",
        "ticket_key",
        "bet_code",
        "final_odds",
        "final_payout",
    ]
    out = out[keep_cols].drop_duplicates(
        subset=["date", "venue_id", "race_no", "ticket_type", "ticket_key"],
        keep="last",
    )

    return out


def merge_odds(step43: pd.DataFrame, odds: pd.DataFrame) -> pd.DataFrame:
    merge_keys = ["date", "venue_id", "race_no", "ticket_type", "ticket_key"]
    out = step43.merge(
        odds,
        on=merge_keys,
        how="left",
    )

    prob = pd.to_numeric(out.get("probability"), errors="coerce")
    if "probability_pct" in out.columns:
        prob_pct = pd.to_numeric(out["probability_pct"], errors="coerce")
        prob = prob.fillna(prob_pct / 100)

    out["expected_return_100yen"] = (prob * out["final_payout"]).round(1)
    out["expected_profit_100yen"] = (out["expected_return_100yen"] - 100).round(1)

    return out


def print_summary(out: pd.DataFrame, step43_path: Path, odds_path: Path):
    print(f"📄 step43: {step43_path}")
    print(f"📄 odds: {odds_path}")
    print(f"📊 rows: {len(out)}")
    print(f"📊 races: {out['race_id'].nunique() if 'race_id' in out.columns else 0}")

    if "ticket_type" in out.columns:
        print("📊 rows by ticket_type:")
        for ticket_type, count in out["ticket_type"].value_counts().sort_index().items():
            print(f"   - {ticket_type}: {count}")

    if "final_odds" in out.columns:
        matched = int(out["final_odds"].notna().sum())
        missing = int(out["final_odds"].isna().sum())
        print(f"📊 odds matched: {matched}")
        print(f"📊 odds missing: {missing}")

    if "ticket_type" in out.columns and "final_odds" in out.columns:
        print("📊 odds missing by ticket_type:")
        for ticket_type, value in out.groupby("ticket_type")["final_odds"].apply(lambda s: int(s.isna().sum())).sort_index().items():
            print(f"   - {ticket_type}: {value}")


def main():
    args = parse_args()
    date = args.date

    print("=" * 72)
    print(f"🚀 START grade01 step04 merge odds | date={date}")
    print("=" * 72)

    step43_path = find_step43_path(date)
    odds_path = find_odds_path(date, args.odds_path)

    step43 = normalize_step43(pd.read_csv(step43_path))
    odds = normalize_odds(pd.read_csv(odds_path), date)
    out = merge_odds(step43, odds)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"grade01_step04_tickets_with_odds_{date}.csv"
    out.to_csv(out_path, index=False)

    print_summary(out, step43_path, odds_path)
    print(f"💾 saved: {out_path}")
    print("=" * 72)
    print(f"🎉 END grade01 step04 merge odds | date={date}")
    print("=" * 72)


if __name__ == "__main__":
    main()