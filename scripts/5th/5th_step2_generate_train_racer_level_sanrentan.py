import pandas as pd
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta

parser = ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()
date = args.date
RESULTS_DIR = Path("data/results")
RACER_STATS_PATH = Path("data/5th/tmp/step1_racer_stats.csv")
OUTPUT_PATH = Path("data/5th/tmp/step2_train_racer_level.csv")

# 2015〜基準年のresults CSVを読み込み
end_year = datetime.strptime(date, "%Y-%m-%d").year
start_year = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3*365)).year
dfs = []
for year in range(start_year, end_year + 1):
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
df_all = df_all[df_all["date"] < pd.to_datetime(date)]
df_all = df_all[df_all["date"] >= pd.to_datetime(date) - pd.Timedelta(days=3*365)]

# 戦法・勝率などの集計データと結合
racer_stats = pd.read_csv(RACER_STATS_PATH)
df_merged = pd.merge(df_all, racer_stats, on="racer_id", how="left")

train_data_list = [df_merged]

train_df = pd.concat(train_data_list, ignore_index=True)

# ラベルデータの読み込みと結合（デバッグ付き）
labels_path = Path("data/5th/step0_arare_labels_merged.csv")
if labels_path.exists():
    labels_df = pd.read_csv(labels_path)
    labels_df["date"] = pd.to_datetime(labels_df["date"])
    train_df["date"] = pd.to_datetime(train_df["date"])

    # Match only on the exact date (day level), remove time component
    labels_df["date"] = labels_df["date"].dt.normalize()
    train_df["date"] = train_df["date"].dt.normalize()

    for col in ["venue_id", "race_no"]:
        labels_df[col] = labels_df[col].astype(int)
        train_df[col] = train_df[col].astype(int)


    train_df = pd.merge(
        train_df,
        labels_df[["date", "venue_id", "race_no", "is_arare"]],
        on=["date", "venue_id", "race_no"],
        how="left"
    )
    print(f"✅ ラベル結合: {labels_df.shape[0]} 件")
    print(f"🧪 is_arare null件数: {train_df['is_arare'].isna().sum()}")
else:
    print(f"⚠️ ラベルファイルが見つかりません: {labels_path}")

# 前日の日付を取得
current_date = datetime.strptime(date, "%Y-%m-%d")
prev_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")

# 前日のフィードバックファイルを結合（5th/荒れ度）
feedback_path = Path(f"data/5th/step7/step7_train_feedback_arare_{prev_date}.csv")
if feedback_path.exists():
    print(f"🔁 前日フィードバック読み込み: {feedback_path}")
    feedback_df = pd.read_csv(feedback_path)
    feedback_df["date"] = pd.to_datetime(feedback_df["date"])
    train_df = pd.merge(
        train_df,
        feedback_df[["date", "venue_id", "race_no", "racer_id", "hit"]],
        on=["date", "venue_id", "race_no", "racer_id"],
        how="left"
    )
else:
    print(f"⚠️ フィードバックファイルなし: {feedback_path}")

# 出力
train_df.to_csv(OUTPUT_PATH, index=False)
print(f"📤 上書き保存: {OUTPUT_PATH}")