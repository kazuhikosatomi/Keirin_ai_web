import sys
import subprocess
from datetime import datetime, timedelta
import pandas as pd
import os

def main(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    delta = timedelta(days=1)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    calendar_path = os.path.join(BASE_DIR, "data/calendar/calendar_all.csv")
    calendar_df = pd.read_csv(calendar_path, dtype=str)
    calendar_df.columns = calendar_df.columns.str.strip()

    while start_date <= end_date:
        date_str = start_date.strftime("%Y-%m-%d")
        date_str_arg = date_str.replace("-", "")
        print(f"\n📅 {date_str} の処理を開始します")

        date_calendar_df = calendar_df[calendar_df["date"] == date_str_arg]
        if date_calendar_df.empty:
            print(f"⚠️ {date_str} のカレンダーにデータがありません")
            start_date += delta
            continue

        try:
            subprocess.run(["python", "scripts/entries/scrape_entry_today_grade.py", date_str], check=True)
        except subprocess.CalledProcessError:
            print(f"❌ エラー: {date_str} の処理に失敗しました")

        start_date += delta

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/entries/scrape_entry_range_from_calendar.py <start_date> <end_date>")
        sys.exit(1)
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    main(start_date, end_date)