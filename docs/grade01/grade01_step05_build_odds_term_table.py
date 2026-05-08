
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step05_build_odds_term_table.py

目的:
グレードレース用のオッズ取得タイミング管理表を作成する。

入力:
- data/grade01/step04/grade01_step04_tickets_with_odds_YYYY-MM-DD.csv があれば優先
- なければ data/sim06/step43/sim06_step43_all_top_tickets_YYYY-MM-DD.csv
- 発走時刻は entry_YYYY-MM-DD.csv から取得する

出力:
- data/grade01/step05/grade01_step05_odds_term_table_YYYY-MM-DD.csv

方針:
- race_id に存在するレースだけを対象にする
- レース番号を固定しない（例: 04R〜12R, 02R〜11R などに対応）
- 原則「前レース発走 + 5分」で odds_fetch_time を作る
- 対象レースが1Rの場合だけ「自身の発走30分前」にする
- 対象レースが1R以外の場合は、対象外レースを含めた前レース発走 + 5分にする
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_DATE = "2026-04-26"
OUT_DIR = Path("data/grade01/step05")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--entry-path", default=None, help="entry CSVを明示指定する場合")
    parser.add_argument("--first-race-minutes-before", type=int, default=30, help="最初の対象レースの取得時刻。自身の発走何分前にするか")
    parser.add_argument("--after-prev-minutes", type=int, default=5, help="2レース目以降。前レース発走何分後にするか")
    return parser.parse_args()


def find_source_path(date: str) -> Path:
    step04_path = Path(f"data/grade01/step04/grade01_step04_tickets_with_odds_{date}.csv")
    step43_path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")

    if step04_path.exists():
        return step04_path
    if step43_path.exists():
        return step43_path

    raise FileNotFoundError(f"source not found: {step04_path} or {step43_path}")


def find_entry_path(date: str, explicit_path: str | None = None) -> Path | None:
    if explicit_path:
        path = Path(explicit_path)
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    year = date[:4]
    candidates = [
        Path(f"data/entries/{year}/entry_{date}.csv"),
        Path(f"data/entry/{year}/entry_{date}.csv"),
        Path(f"data/entries/entry_{date}.csv"),
        Path(f"data/entry_{date}.csv"),
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def parse_race_id(race_id: str):
    # 例: 2026-04-26_42_04R
    parts = str(race_id).split("_")
    date = parts[0]
    venue_id = int(parts[1])
    race_no = int(parts[2].replace("R", ""))
    race_no_label = f"{race_no:02d}R"
    return date, venue_id, race_no, race_no_label


def detect_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def normalize_time_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""

    # すでに HH:MM の場合
    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                hour = int(float(parts[0]))
                minute = int(float(parts[1]))
                return f"{hour:02d}:{minute:02d}"
            except Exception:
                return text

    # 例: 1345 -> 13:45
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 4:
        return f"{int(digits[:2]):02d}:{int(digits[2:]):02d}"
    if len(digits) == 3:
        return f"{int(digits[:1]):02d}:{int(digits[1:]):02d}"

    return text


def load_entry_times(date: str, entry_path: Path | None) -> pd.DataFrame:
    if entry_path is None:
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time"])

    df = pd.read_csv(entry_path)
    if df.empty:
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time"])

    venue_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code"])
    race_col = detect_column(df, ["race_no", "race_num", "race_number", "race"])
    time_col = detect_column(df, ["post_time", "start_time", "race_time", "発走時間", "発走時刻", "締切時刻"])
    date_col = detect_column(df, ["date", "race_date"])

    missing = []
    if venue_col is None:
        missing.append("venue_id")
    if race_col is None:
        missing.append("race_no")
    if time_col is None:
        missing.append("post_time")
    if missing:
        print(f"⚠️ entryから発走時刻を取得できません。missing logical columns: {missing}")
        print(f"🧾 entry columns: {list(df.columns)}")
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time"])

    out = df[[venue_col, race_col, time_col] + ([date_col] if date_col else [])].copy()
    out = out.rename(columns={venue_col: "venue_id", race_col: "race_no", time_col: "post_time"})
    if date_col:
        out = out.rename(columns={date_col: "date"})
    else:
        out["date"] = date

    out["date"] = out["date"].astype(str)
    out["venue_id"] = pd.to_numeric(out["venue_id"], errors="coerce")
    out["race_no"] = pd.to_numeric(out["race_no"], errors="coerce")
    out["post_time"] = out["post_time"].map(normalize_time_text)

    out = out.dropna(subset=["venue_id", "race_no"])
    out["venue_id"] = out["venue_id"].astype(int)
    out["race_no"] = out["race_no"].astype(int)

    out = out[["date", "venue_id", "race_no", "post_time"]].drop_duplicates(
        subset=["date", "venue_id", "race_no"],
        keep="last",
    )
    return out


def add_minutes_to_hhmm(date: str, hhmm: str, minutes: int) -> str:
    if not hhmm:
        return ""
    dt = pd.to_datetime(f"{date} {hhmm}", errors="coerce")
    if pd.isna(dt):
        return ""
    dt = dt + pd.Timedelta(minutes=minutes)
    return dt.strftime("%H:%M")


def build_term_table(
    df: pd.DataFrame,
    entry_times: pd.DataFrame,
    first_race_minutes_before: int,
    after_prev_minutes: int,
) -> pd.DataFrame:
    if "race_id" not in df.columns:
        raise ValueError("source missing race_id")

    race_ids = sorted(df["race_id"].astype(str).unique())

    rows = []
    for race_id in race_ids:
        date, venue_id, race_no, race_no_label = parse_race_id(race_id)
        rows.append(
            {
                "date": date,
                "venue_id": venue_id,
                "race_no": race_no,
                "race_no_label": race_no_label,
                "race_id": race_id,
                "post_time": "",
                "prev_race_no": "",
                "prev_post_time": "",
                "odds_fetch_time": "",
                "fetch_rule": "prev_post_time_plus_5min",
                "status": "pending",
                "fetched_at": "",
                "note": "",
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values(["venue_id", "race_no"]).reset_index(drop=True)

    if not entry_times.empty:
        out = out.merge(entry_times, on=["date", "venue_id", "race_no"], how="left", suffixes=("", "_entry"))
        if "post_time_entry" in out.columns:
            out["post_time"] = out["post_time_entry"].fillna(out["post_time"])
            out = out.drop(columns=["post_time_entry"])

    # 前レース情報を設定。
    # 対象レース一覧だけでなく、entryに存在する全レースから前レース発走時刻を拾う。
    out["prev_race_no"] = ""
    out["prev_post_time"] = ""

    if not entry_times.empty:
        entry_lookup = entry_times.copy()
        entry_lookup["venue_id"] = pd.to_numeric(entry_lookup["venue_id"], errors="coerce").astype("Int64")
        entry_lookup["race_no"] = pd.to_numeric(entry_lookup["race_no"], errors="coerce").astype("Int64")
        entry_map = {
            (int(r.venue_id), int(r.race_no)): str(r.post_time)
            for r in entry_lookup.itertuples(index=False)
            if pd.notna(r.venue_id) and pd.notna(r.race_no)
        }

        for idx, row in out.iterrows():
            race_no = int(row["race_no"])
            venue_id = int(row["venue_id"])
            prev_race_no = race_no - 1
            if prev_race_no >= 1:
                out.at[idx, "prev_race_no"] = prev_race_no
                out.at[idx, "prev_post_time"] = entry_map.get((venue_id, prev_race_no), "")
    else:
        # entryが無い場合のみ、対象レース一覧内の前レースで代用する。
        out["prev_race_no"] = out.groupby("venue_id")["race_no"].shift(1)
        out["prev_post_time"] = out.groupby("venue_id")["post_time"].shift(1)
        out["prev_race_no"] = out["prev_race_no"].fillna("").apply(lambda x: "" if x == "" else int(x))
        out["prev_post_time"] = out["prev_post_time"].fillna("")

    # 取得タイミングを計算（オッズ: 前レース発走+1分 / 結果: 自レース発走+10分）
    out["result_fetch_time"] = ""

    for idx, row in out.iterrows():
        date = row["date"]
        post_time = row.get("post_time", "")
        prev_post_time = row.get("prev_post_time", "")
        race_no = int(row.get("race_no", 0))

        # --- オッズ更新 ---
        if race_no == 1 and post_time:
            # 1Rだけ特例（発走30分前）
            out.at[idx, "odds_fetch_time"] = add_minutes_to_hhmm(date, post_time, -30)
            out.at[idx, "fetch_rule"] = "race1_post_time_minus_30min"

        elif prev_post_time:
            # 通常：前レース発走+1分
            out.at[idx, "odds_fetch_time"] = add_minutes_to_hhmm(date, prev_post_time, 1)
            out.at[idx, "fetch_rule"] = "prev_post_time_plus_1min"

        else:
            out.at[idx, "odds_fetch_time"] = ""
            out.at[idx, "fetch_rule"] = "prev_post_time_missing"

        # --- 結果更新 ---
        if post_time:
            out.at[idx, "result_fetch_time"] = add_minutes_to_hhmm(date, post_time, 10)
        else:
            out.at[idx, "result_fetch_time"] = ""

    return out


def print_summary(out: pd.DataFrame, source_path: Path, entry_path: Path | None):
    print(f"📄 source: {source_path}")
    print(f"📄 entry: {entry_path if entry_path else 'not found'}")
    print(f"📊 rows: {len(out)}")
    print(f"📊 venues: {out['venue_id'].nunique() if 'venue_id' in out.columns else 0}")
    print(f"📊 races: {out['race_id'].nunique() if 'race_id' in out.columns else 0}")
    print(f"📊 post_time filled: {int((out['post_time'].astype(str) != '').sum())}")
    print(f"📊 odds_fetch_time filled: {int((out['odds_fetch_time'].astype(str) != '').sum())}")

    if not out.empty:
        print("📊 races by venue:")
        for venue_id, sub in out.groupby("venue_id"):
            labels = ", ".join(
                f"{r.race_no_label}({r.post_time or '--'}→{r.odds_fetch_time or '--'})"
                for r in sub.itertuples(index=False)
            )
            print(f"   - v{venue_id}: {labels}")


def main():
    args = parse_args()
    date = args.date

    print("=" * 72)
    print(f"🚀 START grade01 step05 build odds term table | date={date}")
    print("=" * 72)

    source_path = find_source_path(date)
    entry_path = find_entry_path(date, args.entry_path)

    df = pd.read_csv(source_path)
    entry_times = load_entry_times(date, entry_path)
    out = build_term_table(
        df,
        entry_times,
        first_race_minutes_before=args.first_race_minutes_before,
        after_prev_minutes=args.after_prev_minutes,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"grade01_step05_odds_term_table_{date}.csv"
    out.to_csv(out_path, index=False)

    print_summary(out, source_path, entry_path)
    print(f"💾 saved: {out_path}")
    print("=" * 72)
    print(f"🎉 END grade01 step05 build odds term table | date={date}")
    print("=" * 72)


if __name__ == "__main__":
    main()