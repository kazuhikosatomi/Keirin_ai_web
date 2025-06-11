import pandas as pd
from pathlib import Path

# 入力パス
RESULTS_DIR = Path("data/results")
RACER_STATS_PATH = Path("data/2nd/racer_stats_2025_2029.csv")
OUTPUT_PATH = Path("data/2nd/train_racer_level_2015_2019.csv")

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

# 出力
df_merged.to_csv(OUTPUT_PATH, index=False)
print(f"📤 保存完了: {OUTPUT_PATH}")