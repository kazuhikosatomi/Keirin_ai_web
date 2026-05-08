

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step09_scrape_result_for_race.py

目的:
チャリロト結果ページから、指定した1レースの結果払戻を取得する。

取得対象:
- 2車単
- 3連複
- 3連単

例:
python3 scripts/grade01/grade01_step09_scrape_result_for_race.py \
  --date 2026-05-03 --venue-id 35 --race-no 1

入力URL:
https://www.chariloto.com/keirin/results/{venue_id}/{date}

出力:
data/grade01/step09/grade01_step09_results_{date}.csv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


DEFAULT_DATE = "2026-05-03"
DEFAULT_VENUE_ID = 35
DEFAULT_RACE_NO = 1
OUT_DIR = Path("data/grade01/step09")


BET_TYPE_MAP = {
    "2車単": {
        "table_title": "2車連",
        "row_label": "単",
    },
    "3連複": {
        "table_title": "3連勝",
        "row_label": "複",
    },
    "3連単": {
        "table_title": "3連勝",
        "row_label": "単",
    },
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--venue-id", type=int, default=DEFAULT_VENUE_ID, help="競輪場ID")
    parser.add_argument("--race-no", type=int, default=DEFAULT_RACE_NO, help="レース番号")
    parser.add_argument("--url", default=None, help="結果ページURLを直接指定する場合")
    parser.add_argument("--output", default=None, help="出力CSVを直接指定する場合")
    return parser.parse_args()


def build_url(date: str, venue_id: int) -> str:
    return f"https://www.chariloto.com/keirin/results/{venue_id}/{date}"


def normalize_numbers(text: str, bet_type: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("=", "-")

    # 3連複は順不同なので、後工程で照合しやすいよう昇順にする
    if bet_type == "3連複":
        nums = [x for x in text.split("-") if x]
        try:
            nums = sorted(nums, key=lambda x: int(x))
        except Exception:
            pass
        return "-".join(nums)

    return text


def parse_yen(text: str) -> int | None:
    text = str(text or "")
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    return int(digits)


def payout_to_odds(payout_yen: int | None) -> float | None:
    if payout_yen is None:
        return None
    return round(payout_yen / 100.0, 1)


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }
    res = requests.get(url, headers=headers, timeout=30)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or "utf-8"
    return res.text


def find_race_section(soup: BeautifulSoup, race_no: int):
    section = soup.select_one(f"section#race{race_no}")
    if section is not None:
        return section
    return None


def find_table_by_title(section, title_text: str):
    for table in section.select("table"):
        th = table.find("th")
        if th and title_text in th.get_text(strip=True):
            return table
    return None


def extract_from_table(table, row_label: str):
    if table is None:
        return "", None

    for tr in table.select("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        label = cells[0].get_text(strip=True)
        if label != row_label:
            continue

        # 例: 5-1 3,900円 / 1=5=7 950円
        value_cell = cells[1]
        p = value_cell.find("p")
        target = p if p else value_cell

        payout_span = target.find("span")
        payout_yen = parse_yen(payout_span.get_text(" ", strip=True) if payout_span else target.get_text(" ", strip=True))

        full_text = target.get_text(" ", strip=True)
        if payout_span:
            full_text = full_text.replace(payout_span.get_text(" ", strip=True), "")

        numbers = full_text.strip()
        numbers = re.sub(r"\s+", "", numbers)
        return numbers, payout_yen

    return "", None


def scrape_result_for_race(date: str, venue_id: int, race_no: int, url: str) -> pd.DataFrame:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    section = find_race_section(soup, race_no)

    if section is None:
        raise ValueError(f"race section not found: race{race_no}")

    rows = []
    for bet_type, setting in BET_TYPE_MAP.items():
        table = find_table_by_title(section, setting["table_title"])
        raw_numbers, payout_yen = extract_from_table(table, setting["row_label"])
        result_numbers = normalize_numbers(raw_numbers, bet_type)

        rows.append(
            {
                "date": date,
                "venue_id": int(venue_id),
                "race_no": int(race_no),
                "bet_type": bet_type,
                "result_numbers": result_numbers,
                "payout_yen": payout_yen,
                "payout_odds": payout_to_odds(payout_yen),
                "source_url": url,
            }
        )

    return pd.DataFrame(rows)


def merge_save(df_new: pd.DataFrame, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        df_old = pd.read_csv(out_path)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(
            subset=["date", "venue_id", "race_no", "bet_type"],
            keep="last",
        )
    else:
        df = df_new.copy()

    df = df.sort_values(["date", "venue_id", "race_no", "bet_type"]).reset_index(drop=True)
    df.to_csv(out_path, index=False)
    return df


def main():
    args = parse_args()
    date = args.date
    venue_id = int(args.venue_id)
    race_no = int(args.race_no)
    url = args.url or build_url(date, venue_id)

    out_path = Path(args.output) if args.output else OUT_DIR / f"grade01_step09_results_{date}.csv"

    print("=" * 72)
    print(f"🚀 START grade01 step09 scrape result | date={date} venue={venue_id} race={race_no}R")
    print("=" * 72)
    print(f"🌐 url: {url}")

    df_new = scrape_result_for_race(date, venue_id, race_no, url)
    df_all = merge_save(df_new, out_path)

    print("📊 scraped:")
    print(df_new[["bet_type", "result_numbers", "payout_yen", "payout_odds"]].to_string(index=False))
    print(f"💾 saved: {out_path}")
    print(f"📊 total rows: {len(df_all)}")
    print("=" * 72)
    print(f"🎉 END grade01 step09 scrape result | date={date} venue={venue_id} race={race_no}R")
    print("=" * 72)


if __name__ == "__main__":
    main()