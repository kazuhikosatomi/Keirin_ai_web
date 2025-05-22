from selenium.webdriver.chrome.options import Options


import pandas as pd
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

# ▼ Selenium オプション設定
options = Options()
options.add_argument('--headless')

try:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
except ValueError:
    print("日付形式が正しくありません。YYYY-MM-DD で指定してください")
    sys.exit(1)

# ▼ データ読み込み
calendar_df = pd.read_csv("data/calendar/keirin_calendar_2024-12_to_2025-06.csv")
calendar_df.rename(columns={"place": "競輪場名"}, inplace=True)
calendar_df["date"] = pd.to_datetime(calendar_df["date"])

jyocode_df = pd.read_csv("data/venue/jyocode.csv")

# ▼ 開催日と場名を突合して (date, vel_code, place_name) を抽出
range_df = calendar_df[(calendar_df["date"] >= start_dt) & (calendar_df["date"] <= end_dt)]
merged_df = pd.merge(range_df, jyocode_df, on="競輪場名", how="inner")
merged_df["date"] = merged_df["date"].dt.strftime("%Y-%m-%d")
filtered_venues = list(merged_df[["date", "Code", "競輪場名"]].itertuples(index=False, name=None))

# ▼ 処理開始
print(f"🎯 期間: {start_date} 〜 {end_date} / 開催日×場数: {len(filtered_venues)}")
odds_url = "https://www.chariloto.com/api/keirin/odds_per_race"

# ▼ 日付ごとにまとめてCSV出力
grouped = {}
for date_str, vel_code, place_name in filtered_venues:
    grouped.setdefault(date_str, []).append((str(vel_code).zfill(2), place_name))

for open_day, venues in grouped.items():
    output_file = f"chariloto_odds_{open_day}.csv"
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["日付", "場名", "場コード", "レース", "賭式", "組番", "オッズ"])

        for vel_code, place_name in venues:
            for race_num in range(1, 13):
                params = {
                    "open_day": open_day,
                    "vel_code": vel_code,
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
                        bet_type = item.get("bet_type")
                        deme = item.get("deme")
                        odds = item.get("normalize_rate")
                        odds_val = 9999.9 if odds is None else odds
                        writer.writerow([open_day, place_name, vel_code, f"{race_num}R", bet_type, deme, odds_val])

                    print(f"✅ {open_day} {place_name} {race_num}R")

                except Exception as e:
                    print(f"⚠️ {open_day} {place_name} {race_num}R: エラー → {e}")
                    continue

    print(f"📁 保存完了: {output_file}")

print("🎉 全期間の処理が完了しました")
