import sys
import requests
import csv
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import os
import pandas as pd
import argparse

def fetch_race_grade(date_str):
    results = []

    # 開催カレンダーから対象venue_id取得
    calendar_path = "data/calendar/calendar_all.csv"
    if not os.path.exists(calendar_path):
        print(f"❌ カレンダーファイルが見つかりません: {calendar_path}")
        return results

    calendar_df = pd.read_csv(calendar_path, dtype={"date": str, "venue_id": str})
    calendar_df["date"] = pd.to_datetime(calendar_df["date"], format="%Y%m%d").dt.strftime("%Y-%m-%d")
    target_df = calendar_df[calendar_df["date"] == date_str]
    venue_ids = target_df["venue_id"].unique().tolist()

    race_nums = list(range(1, 13))

    for venue_id in venue_ids:
        for race_no in race_nums:
            url = f"https://www.chariloto.com/keirin/athletes/{date_str}/{venue_id}/{race_no}"
            try:
                res = requests.get(url, timeout=5)
                if res.status_code != 200:
                    continue
                soup = BeautifulSoup(res.content, "html.parser")
                heading = soup.select_one("h2.heading-title")
                if heading:
                    text = heading.get_text()
                    match_grade = re.search(r"\b(GP|G[1-3]|F[1-2])\b", text)
                    race_grade = match_grade.group(1) if match_grade else ""

                    class_name = ""
                    if race_grade:
                        before_grade = text.split(race_grade)[0]
                        lines = before_grade.strip().splitlines()
                        lines = [l.strip() for l in lines if l.strip()]
                        if lines:
                            class_name = lines[-1].replace("　", "").replace(" ", "")

                    results.append({
                        "date": date_str,
                        "venue_id": venue_id,
                        "race_no": race_no,
                        "race_grade": race_grade,
                        "class_name": class_name
                    })
            except Exception as e:
                print(f"⚠️ Error at {url}: {e}")
                continue

    return results

def save_to_csv(data, date_str):
    output_dir = f"data/race_grade/{date_str[:4]}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"race_grade_{date_str}.csv")
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "venue_id", "race_no", "race_grade", "class_name"])
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ 出力完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--target", help="Single date (YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        if args.target:
            start_date = end_date = datetime.strptime(args.target, "%Y-%m-%d")
        elif args.start and args.end:
            start_date = datetime.strptime(args.start, "%Y-%m-%d")
            end_date = datetime.strptime(args.end, "%Y-%m-%d")
        else:
            print("❌ 日付指定が不正です。--target または --start/--end を指定してください。")
            sys.exit(1)
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"📅 {date_str} のレースグレードを取得中...")
        results = fetch_race_grade(date_str)
        save_to_csv(results, date_str)
        current_date += timedelta(days=1)