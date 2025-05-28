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

# ▼ コマンドライン引数の処理（--targetオプション）
parser = argparse.ArgumentParser()
parser.add_argument("--target", help="対象日付 (YYYY-MM-DD)")
args = parser.parse_args()

if args.target:
    start_date = end_date = args.target
else:
    yesterday = datetime.now() - timedelta(days=1)
    start_date = end_date = yesterday.strftime("%Y-%m-%d")

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

# ▼ 処理開始
print(f"🎯 期間: {start_date} 〜 {end_date} / 開催日×場数: {len(filtered_venues)}")
odds_url = "https://www.chariloto.com/api/keirin/odds_per_race"

grouped = {}
for date_str, venue_id in filtered_venues:
    grouped.setdefault(date_str, []).append(str(int(venue_id)).zfill(2))

for open_day, venue_ids in grouped.items():
    year = open_day[:4]
    output_dir = os.path.join(script_dir, f"../../data/odds/{year}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"odds_{open_day}.csv")

    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.writer(f)
        header = ["date", "venue_id", "race_no", "bet_code", "car_1", "car_2", "car_3", "odds_1", "odds_2"]
        writer.writerow(header)

        for venue_id in venue_ids:
            print(f"🔄 {open_day}（{venue_id}）")
            total_rows = 0
            for race_num in range(1, 13):
                params = {
                    "open_day": open_day,
                    "vel_code": venue_id,
                    "race_num": str(race_num)
                }

                try:
                    response = requests.get(odds_url, params=params)
                    time.sleep(0.4)

                    if response.status_code != 200:
                        break

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
                        car_1 = int(cars[0]) if len(cars) > 0 else None
                        car_2 = int(cars[1]) if len(cars) > 1 else None
                        car_3 = int(cars[2]) if len(cars) > 2 else None

                        row = [open_day, int(venue_id), race_num, bet_code, car_1, car_2, car_3, odds_1, odds_2]
                        writer.writerow(row)
                        total_rows += 1

                except Exception:
                    continue

            if total_rows > 0:
                print(f"✅ {total_rows}件取得")
            else:
                print("⚠️ オッズなし")

    print(f"📅 対象日: {open_day}")
    print(f"🎯 出力件数: {total_rows}")
    print(f"\n🎉 出力完了: {output_file}")

print("🎉 全期間の処理が完了しました")
