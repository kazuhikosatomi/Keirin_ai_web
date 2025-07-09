import pandas as pd
import os
import argparse
from datetime import datetime, timedelta
from glob import glob

parser = argparse.ArgumentParser()
parser.add_argument('--start', help='Start date (YYYY-MM-DD)')
parser.add_argument('--end', help='End date (YYYY-MM-DD)')
args = parser.parse_args()

if args.start and args.end:
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")
    date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range((end_date - start_date).days + 1)]
else:
    files = glob("data/results/2025/results_2025-*.csv")
    date_list = [os.path.basename(f).replace("results_", "").replace(".csv", "") for f in files]

for date_str in sorted(date_list):
    print(f"📅 処理中: {date_str}")
    try:
        year = date_str[:4]
        results_path = f"data/results/{year}/results_{date_str}.csv"
        grade_path = f"data/race_grade/{year}/race_grade_{date_str}.csv"
        output_dir = f"data/results/with_grade/{year}"
        os.makedirs(output_dir, exist_ok=True)
        output_path = f"{output_dir}/results_{date_str}.csv"

        df_results = pd.read_csv(results_path)
        df_grade = pd.read_csv(grade_path)

        df_results["race_no"] = df_results["race_no"].astype(int)
        df_grade["race_no"] = df_grade["race_no"].astype(int)

        merged = pd.merge(df_results, df_grade, on=["date", "venue_id", "race_no"], how="left")
        merged.to_csv(output_path, index=False)
        print(f"✅ 保存完了: {output_path}")

    except Exception as e:
        print(f"❌ エラー ({date_str}): {e}")
