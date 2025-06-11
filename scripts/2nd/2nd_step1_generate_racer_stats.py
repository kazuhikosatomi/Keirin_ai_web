import pandas as pd
from pathlib import Path

# 結果格納用リスト
all_results = []

# 2025〜2029年のCSVファイルを読み込む
for year in range(2025, 2030):
    folder = Path(f"data/results/{year}")
    csv_files = folder.glob("*.csv")
    for file in csv_files:
        df = pd.read_csv(file)
        all_results.append(df)

# 全部まとめて連結
results_df = pd.concat(all_results, ignore_index=True)
print(f"✅ 結合済み: {len(results_df)}件")

# 戦法ごとのダミーフラグ列を追加
results_df["style_escape"] = (results_df["finish_tactics"] == "逃").astype(int)
results_df["style_sprint"] = (results_df["finish_tactics"] == "捲").astype(int)
results_df["style_chase"] = (results_df["finish_tactics"] == "差").astype(int)
results_df["style_other"] = (results_df["finish_tactics"] == "マ").astype(int)

# 着順の数値変換（例: '1'〜'9' を int に、LC/DS などは NaN に）
results_df["rank"] = pd.to_numeric(results_df["rank"], errors="coerce")

# 集計処理
agg = results_df.groupby("racer_id").agg(
    races=("rank", "count"),
    win_rate=("rank", lambda x: (x == 1).mean()),
    top2_rate=("rank", lambda x: (x <= 2).mean()),
    top3_rate=("rank", lambda x: (x <= 3).mean()),
    style_escape=("style_escape", "sum"),
    style_sprint=("style_sprint", "sum"),
    style_chase=("style_chase", "sum"),
    style_other=("style_other", "sum"),
).reset_index()

# 保存
output_path = "data/2nd/racer_stats_2025_2029.csv"
agg.to_csv(output_path, index=False)
print(f"📤 保存完了: {output_path}")