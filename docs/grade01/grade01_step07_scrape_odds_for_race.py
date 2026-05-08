import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "..", "..", "data", "master", "bet_master.csv")
bet_master_df = pd.read_csv(csv_path)
bet_type_to_code = dict(zip(bet_master_df["bet_type"], bet_master_df["bet_code"]))

bet_code_to_type = dict(zip(bet_master_df["bet_code"], bet_master_df["bet_type"]))

import requests
import csv
import time
import sys
from datetime import datetime, timedelta
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="対象日付 (YYYY-MM-DD) ※単一日指定")
parser.add_argument("--venue-id", type=int, required=True, help="対象競輪場ID")
parser.add_argument("--race-no", type=int, required=True, help="対象レース番号")
args = parser.parse_args()

start_date = end_date = args.date

try:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
except ValueError:
    print("日付形式が正しくありません。YYYY-MM-DD で指定してください")
    sys.exit(1)

import os

script_dir = os.path.dirname(os.path.abspath(__file__))
calendar_path = os.path.join(script_dir, "../../data/calendar/calendar_all.csv")

if not os.path.exists(calendar_path):
    raise FileNotFoundError(f"{calendar_path} が見つかりません。")

calendar_df = pd.read_csv(calendar_path)
# venue情報も読み込み（今後の分析に使用予定）
venue_path = os.path.join(script_dir, "..", "..", "data", "master", "venue_master.csv")
venue_df = pd.read_csv(venue_path)

calendar_df["date"] = pd.to_datetime(calendar_df["date"].astype(str), format="%Y%m%d")
merged_df = pd.merge(calendar_df, venue_df, on="venue_id", how="inner")

# 対象日付範囲に絞り込み
range_df = merged_df[(merged_df["date"] >= start_dt) & (merged_df["date"] <= end_dt)].copy()
range_df["date"] = range_df["date"].dt.strftime("%Y-%m-%d")

filtered_venues = list(range_df[["date", "venue_id"]].itertuples(index=False, name=None))

# venue_id → venue_name 辞書
venue_map = dict(zip(venue_df["venue_id"], venue_df["venue_name"]))

import time
start_all = time.time()
print("\n" + "=" * 60)
print(f"🟢 START grade01_step07_scrape_odds_for_race.py : {start_date} v{args.venue_id} {args.race_no}R")
print("=" * 60 + "\n")

# ▼ 処理開始
# grade01専用: 指定された1場だけに絞る
filtered_venues = [
    (date_str, venue_id)
    for date_str, venue_id in filtered_venues
    if int(venue_id) == int(args.venue_id)
]

target_race_nums = [int(args.race_no)]

print(f"🎯 期間: {start_date} 〜 {end_date} / 対象場数: {len(filtered_venues)}")
print(f"🎯 venue_id指定: {args.venue_id}")
print(f"🎯 race_no指定: {args.race_no}")
odds_url = "https://www.chariloto.com/api/keirin/odds_per_race"

grouped = {}
for date_str, venue_id in filtered_venues:
    grouped.setdefault(date_str, []).append(str(int(venue_id)).zfill(2))

for open_day, venue_ids in grouped.items():
    year = open_day[:4]
    output_dir = os.path.join(script_dir, f"../../data/grade01/odds/{year}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"grade01_odds_{open_day}.csv")

    header = ["date", "venue_id", "race_no", "bet_code", "car_1", "car_2", "car_3", "odds_1", "odds_2"]
    new_rows = []

    for venue_id in venue_ids:
        venue_name = venue_map.get(int(venue_id), "")
        start_venue = time.time()
        print(f"▶ {venue_id} {venue_name} {args.race_no}R ...", end="", flush=True)
        total_rows = 0

        for race_num in target_race_nums:
            params = {
                "open_day": open_day,
                "vel_code": venue_id,
                "race_num": str(race_num)
            }

            try:
                response = requests.get(odds_url, params=params)
                time.sleep(0.4)

                if response.status_code != 200:
                    raise RuntimeError(f"HTTP {response.status_code}: {response.text[:120]}")

                data = response.json()
                if not data.get("odds"):
                    continue

                for item in data["odds"]:
                    bet_type_orig = item.get("bet_type")
                    bet_code = bet_type_to_code.get(bet_type_orig, "")
                    bet_type = bet_code_to_type.get(str(bet_code), "")
                    car_nums = item.get("deme", "")
                    odds_raw = item.get("normalize_rate")
                    if isinstance(odds_raw, str) and "〜" in odds_raw:
                        odds_1, odds_2 = odds_raw.split("〜")
                        odds_1 = float(odds_1)
                        odds_2 = float(odds_2)
                    else:
                        odds_1 = float(odds_raw) if odds_raw else 9999.9
                        odds_2 = ""

                    cars = car_nums.split("-")
                    car_1 = int(cars[0]) if len(cars) > 0 and cars[0] else None
                    car_2 = int(cars[1]) if len(cars) > 1 and cars[1] else None
                    car_3 = int(cars[2]) if len(cars) > 2 and cars[2] else None

                    row = [open_day, int(venue_id), race_num, bet_code, car_1, car_2, car_3, odds_1, odds_2]
                    new_rows.append(row)
                    total_rows += 1

            except Exception as e:
                print(f" error={e}", end="", flush=True)
                continue

        elapsed = time.time() - start_venue
        print(f" done ({elapsed:.1f}s, rows={total_rows})")

    # 既存CSVを読み込み、対象1場1レース分だけ差し替える。
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
    else:
        existing_df = pd.DataFrame(columns=header)

    for col in header:
        if col not in existing_df.columns:
            existing_df[col] = ""

    if not existing_df.empty:
        mask = existing_df["date"].astype(str).eq(open_day)
        mask &= existing_df["venue_id"].astype(int).eq(int(args.venue_id))
        mask &= existing_df["race_no"].astype(int).eq(int(args.race_no))
        existing_df = existing_df[~mask].copy()

    new_df = pd.DataFrame(new_rows, columns=header)
    output_df = pd.concat([existing_df[header], new_df], ignore_index=True)
    if not output_df.empty:
        output_df = output_df.sort_values(["date", "venue_id", "race_no", "bet_code", "car_1", "car_2", "car_3"]).reset_index(drop=True)
    output_df.to_csv(output_file, index=False, encoding="utf-8-sig")

total_elapsed = time.time() - start_all
print("\n" + "=" * 60)
print(f"✅ DONE  grade01_step07_scrape_odds_for_race.py : {total_elapsed:.1f}s")
print("=" * 60)
