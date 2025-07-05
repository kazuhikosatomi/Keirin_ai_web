import pandas as pd
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta

parser = ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()
date = args.date
RESULTS_DIR = Path("data/results")
RACER_STATS_PATH = Path("data/1st/tmp/step1_racer_stats.csv")
OUTPUT_PATH = Path("data/1st/tmp/step2_train_racer_level.csv")

# 2015年から基準日前日までのresults CSVのみ読み込み
dfs = []
current_date = datetime.strptime(date, "%Y-%m-%d")
cutoff_date = current_date - timedelta(days=1)
start_date = cutoff_date - timedelta(days=365*1)
for year in range(2015, cutoff_date.year + 1):
    for file in sorted((RESULTS_DIR / str(year)).glob("results_*.csv")):
        file_date_str = file.stem.split("_")[-1]
        file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
        if start_date <= file_date <= cutoff_date:
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

df_merged = None  # initialize to avoid reference before assignment

# 戦法・勝率などの集計データと結合
racer_stats = pd.read_csv(RACER_STATS_PATH)
df_merged = pd.merge(df_all, racer_stats, on="racer_id", how="left")

df_merged["date"] = pd.to_datetime(df_merged["date"])
df_merged["line_id"] = df_merged["line_id"].fillna(-1).astype(int)

train_data_list = [df_merged]

train_df = pd.concat(train_data_list, ignore_index=True)

# 1年分のフィードバックファイルをまとめて読み込み
feedback_dir = Path("data/1st/step7")
feedback_dfs = []
for file in sorted(feedback_dir.glob("step7_train_feedback_only_niren_*.csv")):
    file_date_str = file.stem.split("_")[-1]
    try:
        file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
    except ValueError:
        continue
    if start_date <= file_date <= cutoff_date:
        df_fb = pd.read_csv(file)
        if "hit" in df_fb.columns:
            df_fb = df_fb[["racer_id", "date", "race_no", "hit"]]
            df_fb["date"] = pd.to_datetime(df_fb["date"])
            df_fb["race_no"] = df_fb["race_no"].astype(int)
            feedback_dfs.append(df_fb)

# 結合してマージ
if feedback_dfs:
    feedback_all = pd.concat(feedback_dfs, ignore_index=True)
    train_df["date"] = pd.to_datetime(train_df["date"])
    train_df["race_no"] = train_df["race_no"].astype(int)
    train_df = pd.merge(train_df, feedback_all, on=["racer_id", "date", "race_no"], how="left")
    print(f"🔁 フィードバック結合: {len(feedback_all)} 件")
else:
    print("⚠️ 有効なフィードバックファイルが見つかりませんでした")

# 出力
train_df.to_csv(OUTPUT_PATH, index=False)
print(f"📤 上書き保存: {OUTPUT_PATH}")