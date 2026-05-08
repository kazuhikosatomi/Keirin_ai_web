#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step06_watch_odds_updates.py

目的:
step05 のオッズ取得タームテーブルを1分ごとに監視し、
odds_fetch_time を過ぎた pending レースだけ処理する。

処理:
1. term_table を読む
2. odds_fetch_time <= 現在時刻 かつ status=pending のレースを抽出
3. dueになったレース番号以降の全レースについて、scripts/grade01/grade01_step07_scrape_odds_for_race.py を順番に実行
4. step04 でオッズ結合
5. step01 で対象レース以降のHTMLを更新
6. term_table の status は due になった行だけ done に更新する

注意:
- due行ごとに、そのレース以降を再取得する。未来レースのstatusはpendingのまま残す
- --once を付けると1回だけチェックして終了
- --dry-run を付けると実行せず対象確認だけ行う
"""

from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
import os

import pandas as pd

PYTHON = os.environ.get("PYTHON", "python3")


DEFAULT_DATE = "2026-04-26"
TERM_DIR = Path("data/grade01/step05")

SCRAPE_ODDS_SCRIPT = Path("scripts/grade01/grade01_step07_scrape_odds_for_race.py")
RESULT_SCRIPT = Path("scripts/grade01/grade01_step09_scrape_result_for_race.py")
def scrape_result_for_race_cmd(date: str, venue_id: str, race_no: str):
    if not RESULT_SCRIPT.exists():
        raise FileNotFoundError(RESULT_SCRIPT)
    cmd = [
        PYTHON,
        str(RESULT_SCRIPT),
        "--date", date,
        "--venue-id", str(int(float(venue_id))),
        "--race-no", str(int(float(race_no))),
    ]
    run_command(cmd)

# --- downstream helper functions ---
def process_result_rows(args) -> int:
    date = args.date
    df = load_term_table(date)
    current = now_hhmm()

    if "result_fetch_time" not in df.columns:
        return 0

    # result_status列がなければ作成
    if "result_status" not in df.columns:
        df["result_status"] = "pending"

    pending_mask = df["result_status"].astype(str).str.lower().eq("pending")
    due_mask = df["result_fetch_time"].map(lambda x: is_due(str(x), current))
    due_df = df[pending_mask & due_mask].copy()

    if due_df.empty:
        return 0

    processed = 0

    for idx, row in due_df.iterrows():
        race_id = str(row["race_id"])
        venue_id = str(row["venue_id"])
        race_no = str(row["race_no"])

        print(f"🏁 result due: {race_id} v{venue_id} {race_no}R")

        if args.dry_run:
            continue

        try:
            df.at[idx, "result_status"] = "running"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = "fetching result"
            save_term_table(date, df)

            # 結果取得（該当レースのみ）
            scrape_result_for_race_cmd(date, venue_id, race_no)

            # 該当レースHTMLのみ更新
            update_one_race_html(
                date=date,
                race_id=race_id,
                top_exacta=args.top_exacta,
                top_trifecta=args.top_trifecta,
                top_trio=args.top_trio,
            )

            update_today_html(date)

            run_command([
                PYTHON,
                "scripts/grade01/grade01_step08_git_publish.py"
            ])

            df.at[idx, "result_status"] = "done"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = "result fetched"
            save_term_table(date, df)

            processed += 1
            print(f"✅ result done: {race_id}")

        except Exception as e:
            df.at[idx, "result_status"] = "error"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = str(e)
            save_term_table(date, df)
            print(f"❌ result error: {race_id} {e}")

    return processed


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=60, help="監視間隔 秒")
    parser.add_argument("--once", action="store_true", help="1回だけチェックして終了")
    parser.add_argument("--dry-run", action="store_true", help="対象確認のみ。処理は実行しない")
    parser.add_argument("--top-exacta", type=int, default=5)
    parser.add_argument("--top-trifecta", type=int, default=10)
    parser.add_argument("--top-trio", type=int, default=5)
    return parser.parse_args()


def term_path(date: str) -> Path:
    return TERM_DIR / f"grade01_step05_odds_term_table_{date}.csv"


def load_term_table(date: str) -> pd.DataFrame:
    path = term_path(date)
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, dtype=str).fillna("")
    return df


def save_term_table(date: str, df: pd.DataFrame):
    path = term_path(date)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_due(fetch_time: str, current_hhmm: str) -> bool:
    if not fetch_time:
        return False
    try:
        return fetch_time <= current_hhmm
    except Exception:
        return False


# 日付を考慮した発走時刻判定
def is_due_for_date(target_date: str, fetch_time: str, current_hhmm: str) -> bool:
    """
    HH:MMだけの比較だと、日付をまたいだ後に
    16:30 <= 00:37 が False になってしまう。

    対象日が今日より前なら、時刻はすでに到達済みとして扱う。
    対象日が今日なら、通常のHH:MM比較を使う。
    """
    if not fetch_time:
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    if str(target_date) < today:
        return True
    return is_due(fetch_time, current_hhmm)



def parse_race_id(race_id: str):
    # 例: 2026-04-26_42_04R
    parts = str(race_id).split("_")
    date = parts[0]
    venue_id = parts[1]
    race_no = parts[2].replace("R", "")
    return date, venue_id, race_no


# --- downstream helper functions ---

def normalize_int(value, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def downstream_rows(df: pd.DataFrame, venue_id: str, race_no: str) -> pd.DataFrame:
    """
    dueになったレース番号以降の同場レースを返す。
    statusは見ない。未来レースも先にオッズ取得・HTML更新するため。
    """
    work = df.copy()
    target_venue_id = normalize_int(venue_id)
    target_race_no = normalize_int(race_no)

    work["__venue_id"] = work["venue_id"].map(normalize_int)
    work["__race_no"] = work["race_no"].map(normalize_int)

    sub = work[(work["__venue_id"] == target_venue_id) & (work["__race_no"] >= target_race_no)].copy()
    sub = sub.sort_values("__race_no").reset_index(drop=True)
    return sub


def run_command(cmd: list[str]):
    print("▶ 実行:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def scrape_odds_for_race(date: str, venue_id: str, race_no: str):
    """
    grade01専用の1場1レースオッズ取得スクリプトを呼ぶ。
    """
    if not SCRAPE_ODDS_SCRIPT.exists():
        raise FileNotFoundError(SCRAPE_ODDS_SCRIPT)

    cmd = [
        PYTHON,
        str(SCRAPE_ODDS_SCRIPT),
        "--date",
        date,
        "--venue-id",
        str(int(float(venue_id))),
        "--race-no",
        str(int(float(race_no))),
    ]
    run_command(cmd)


def merge_odds(date: str):
    cmd = [
        PYTHON,
        "scripts/grade01/grade01_step04_merge_odds.py",
        "--date",
        date,
    ]
    run_command(cmd)


def update_one_race_html(date: str, race_id: str, top_exacta: int, top_trifecta: int, top_trio: int):
    _, venue_id, race_no = parse_race_id(race_id)
    output_path = Path(f"docs/grade/races/v{venue_id}/r{race_no}.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        PYTHON,
        "scripts/grade01/grade01_step01_generate_sample_race_html.py",
        "--date", date,
        "--race-id", race_id,
        "--top-exacta", str(top_exacta),
        "--top-trifecta", str(top_trifecta),
        "--top-trio", str(top_trio),
        "--output", str(output_path),
    ]
    run_command(cmd)


def update_today_html(date: str):
    cmd = [
        PYTHON,
        "scripts/grade01/grade01_step02_generate_today_html.py",
        "--date", date,
    ]
    run_command(cmd)


def process_final_race_confirm(args) -> int:
    """
    最終レースの発走時刻を過ぎたら、最後にもう一度HTMLを更新して
    最終レースの表示を「オッズ確定」状態にする。

    通常のオッズ取得は、最終前レースの5分後に最終レースまで取得済み。
    さらに最終レース発走時刻を過ぎたら、最終レースだけもう一度オッズ取得し、
    step04再結合後にHTML再生成・today再生成・GitHub反映を行う。
    """
    date = args.date
    df = load_term_table(date)
    current = now_hhmm()

    if "post_time" not in df.columns:
        print("ℹ️ final confirm skip: post_time column not found")
        return 0

    required = ["race_id", "venue_id", "race_no", "post_time", "status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"ℹ️ final confirm skip: missing columns: {missing}")
        return 0

    work = df.copy()
    work["__venue_id"] = work["venue_id"].map(normalize_int)
    work["__race_no"] = work["race_no"].map(normalize_int)

    max_race_by_venue = work.groupby("__venue_id")["__race_no"].transform("max")
    final_mask = work["__race_no"].eq(max_race_by_venue)
    done_mask = work["status"].astype(str).str.lower().eq("done")
    post_due_mask = work["post_time"].map(lambda x: is_due_for_date(date, str(x), current))

    if "note" not in df.columns:
        df["note"] = ""
        work["note"] = ""

    already_confirmed_mask = work["note"].astype(str).str.contains("final race confirmed", na=False)
    target_df = work[final_mask & done_mask & post_due_mask & (~already_confirmed_mask)].copy()

    if target_df.empty:
        return 0

    processed = 0
    for idx, row in target_df.iterrows():
        race_id = str(row["race_id"])
        post_time = str(row["post_time"])
        print(f"🏁 final race confirm: {race_id} post_time={post_time} current={current}")

        if args.dry_run:
            continue

        try:
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = "final race confirming"
            save_term_table(date, df)

            # 最終レース発走時刻で最後にもう一度オッズ取得する。
            # これによりHTML上の「オッズ xx:xx現在」も最新化される。
            scrape_odds_for_race(
                date=date,
                venue_id=str(row["venue_id"]),
                race_no=str(row["race_no"]),
            )
            merge_odds(date)

            update_one_race_html(
                date=date,
                race_id=race_id,
                top_exacta=args.top_exacta,
                top_trifecta=args.top_trifecta,
                top_trio=args.top_trio,
            )
            update_today_html(date)
            run_command([
                PYTHON,
                "scripts/grade01/grade01_step08_git_publish.py"
            ])

            df.at[idx, "status"] = "done"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = "final race confirmed at post_time"
            save_term_table(date, df)
            processed += 1
            print(f"✅ final confirmed: {race_id}")

        except Exception as e:
            df.at[idx, "status"] = "error"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = f"final confirm error: {e}"
            save_term_table(date, df)
            print(f"❌ final confirm error: {race_id} {e}")

    return processed

def process_due_rows(args) -> int:
    date = args.date
    df = load_term_table(date)
    current = now_hhmm()

    print("-" * 72)
    print(f"🕒 check {now_stamp()} current={current}")

    required = ["race_id", "venue_id", "race_no", "odds_fetch_time", "status"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"term table missing columns: {missing}")

    pending_mask = df["status"].astype(str).str.lower().eq("pending")
    due_mask = df["odds_fetch_time"].map(lambda x: is_due(str(x), current))
    due_df = df[pending_mask & due_mask].copy()

    print(f"📊 pending: {int(pending_mask.sum())}")
    print(f"📊 due: {len(due_df)}")

    if due_df.empty:
        return 0

    processed = 0
    for idx, row in due_df.iterrows():
        race_id = str(row["race_id"])
        venue_id = str(row["venue_id"])
        race_no = str(row["race_no"])
        fetch_time = str(row["odds_fetch_time"])

        print(f"🎯 due race: {race_id} v{venue_id} {race_no}R fetch_time={fetch_time}")

        if args.dry_run:
            continue

        try:
            df.at[idx, "status"] = "running"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = "processing downstream races"
            save_term_table(date, df)

            # due行は「次レース」を指すが、発走1分後には直前レースのオッズも確定している想定。
            # 例: 8Rのodds_fetch_time = 7R発走+1分 の場合、7R以降を再取得・再生成する。
            update_start_race_no = max(1, normalize_int(race_no) - 1)
            targets = downstream_rows(df, venue_id, str(update_start_race_no))
            print(f"📊 downstream targets: {len(targets)} start={update_start_race_no}R")

            # dueになったレース以降をすべて取得する。
            # ただし未来レースのterm_table statusはpendingのまま残す。
            for _, target in targets.iterrows():
                target_race_id = str(target["race_id"])
                target_venue_id = str(target["venue_id"])
                target_race_no = str(target["race_no"])
                print(f"  ↳ scrape/update target: {target_race_id}")
                scrape_odds_for_race(date, target_venue_id, target_race_no)

            merge_odds(date)

            for _, target in targets.iterrows():
                target_race_id = str(target["race_id"])
                update_one_race_html(
                    date=date,
                    race_id=target_race_id,
                    top_exacta=args.top_exacta,
                    top_trifecta=args.top_trifecta,
                    top_trio=args.top_trio,
                )

            update_today_html(date)
            # GitHubへ反映
            run_command([
                PYTHON,
                "scripts/grade01/grade01_step08_git_publish.py"
            ])

            df.at[idx, "status"] = "done"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = f"odds updated downstream races: {len(targets)}"
            save_term_table(date, df)
            processed += 1
            print(f"✅ done: {race_id} downstream={len(targets)}")

        except Exception as e:
            df.at[idx, "status"] = "error"
            df.at[idx, "fetched_at"] = now_stamp()
            df.at[idx, "note"] = str(e)
            save_term_table(date, df)
            print(f"❌ error: {race_id} {e}")

    return processed


def main():
    args = parse_args()

    print("=" * 72)
    print(f"🚀 START grade01 step06 watch odds updates | date={args.date}")
    print("=" * 72)
    print(f"📌 interval: {args.interval}s")
    print(f"📌 once: {args.once}")
    print(f"📌 dry_run: {args.dry_run}")

    while True:
        process_due_rows(args)
        process_result_rows(args)
        process_final_race_confirm(args)

        if args.once:
            break

        time.sleep(args.interval)

    print("=" * 72)
    print(f"🎉 END grade01 step06 watch odds updates | date={args.date}")
    print("=" * 72)


if __name__ == "__main__":
    main()