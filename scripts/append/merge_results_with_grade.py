import os
import argparse
import pandas as pd
from datetime import datetime, timedelta

# 引数処理
parser = argparse.ArgumentParser()
parser.add_argument("--start", help="開始日 (YYYY-MM-DD)")
parser.add_argument("--end", help="終了日 (YYYY-MM-DD)")
parser.add_argument("--target", help="単一日付 (YYYY-MM-DD)")
args = parser.parse_args()

try:
    if args.target:
        START_DATE = END_DATE = args.target
    elif args.start and args.end:
        START_DATE = args.start
        END_DATE = args.end
    else:
        print("❌ 日付指定が不正です。--target または --start/--end を指定してください。")
        exit(1)
except ValueError:
    print("❌ 日付フォーマットが不正です。YYYY-MM-DD 形式で指定してください。")
    exit(1)

# パス設定
RESULTS_DIR = "data/results"
GRADE_DIR = "data/race_grade"
OUTPUT_DIR = "data/results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 日付ループ
current = datetime.strptime(START_DATE, "%Y-%m-%d")
end = datetime.strptime(END_DATE, "%Y-%m-%d")

while current <= end:
    date_str = current.strftime("%Y-%m-%d")
    year_str = current.strftime("%Y")

    result_path = os.path.join(RESULTS_DIR, year_str, f"results_{date_str}.csv")
    grade_path = os.path.join(GRADE_DIR, year_str, f"race_grade_{date_str}.csv")
    output_path = os.path.join(OUTPUT_DIR, year_str)
    os.makedirs(output_path, exist_ok=True)
    output_file = os.path.join(output_path, f"results_{date_str}.csv")

    if os.path.exists(result_path) and os.path.exists(grade_path):
        df_results = pd.read_csv(result_path)
        df_grade = pd.read_csv(grade_path)

        merged = df_results.merge(df_grade, on=["date", "venue_id", "race_no"], how="left")
        merged.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"✅ {date_str} マージ完了: {output_file}")
    else:
        print(f"⚠️ {date_str} スキップ（ファイルなし）")

    current += timedelta(days=1)