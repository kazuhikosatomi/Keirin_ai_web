import pandas as pd
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta

parser = ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()
date = args.date
RESULTS_DIR = Path("data/results")
RACER_STATS_PATH = Path("data/4th/tmp/step1_racer_stats.csv")
OUTPUT_PATH = Path("data/4th/tmp/step2_train_racer_level.csv")

# 2015〜2019年のresults CSVを読み込み
dfs = []
for year in range(2015, 2020):
    for file in sorted((RESULTS_DIR / str(year)).glob("results_*.csv")):
        df = pd.read_csv(file)
        dfs.append(df)

# 結合・整形
df_all = pd.concat(dfs, ignore_index=True)
print(f"✅ 結合済み: {len(df_all)} 件")

# 必要な列だけ抽出
columns = [
    "racer_id", "date", "car_no", "rank", "line_pos", "line_id",
    "grade", "venue_id", "prefecture", "race_no", "age"
]
df_all = df_all[columns]
df_all["date"] = pd.to_datetime(df_all["date"])

# 戦法・勝率などの集計データと結合
racer_stats = pd.read_csv(RACER_STATS_PATH)
df_merged = pd.merge(df_all, racer_stats, on="racer_id", how="left")

train_data_list = [df_merged]

train_df = pd.concat(train_data_list, ignore_index=True)

# 前日の日付を取得
current_date = datetime.strptime(date, "%Y-%m-%d")
prev_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")

# 前日のフィードバックファイルを結合（存在すれば）
feedback_path = Path(f"data/4th/step7/step7_train_feedback_only_trio_{prev_date}.csv")
if feedback_path.exists():
    print(f"🔁 前日フィードバック読み込み: {feedback_path}")
    feedback_df = pd.read_csv(feedback_path)
    train_df = pd.concat([train_df, feedback_df], ignore_index=True)
else:
    print(f"⚠️ フィードバックファイルなし: {feedback_path}")

# 出力
train_df.to_csv(OUTPUT_PATH, index=False)
print(f"📤 上書き保存: {OUTPUT_PATH}")