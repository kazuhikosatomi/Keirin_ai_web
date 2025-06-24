import pandas as pd
import os

# 日付固定（2025-06-22）
DATE = "2025-06-22"
results_path = f"data/results/2025/results_{DATE}.csv"
odds_path = f"data/odds/2025/odds_{DATE}.csv"
output_path = f"data/7th/arare_label_{DATE}.csv"

# ファイル読み込み
results = pd.read_csv(results_path)
odds = pd.read_csv(odds_path)

# 三連単（bet_code == 5）の最大オッズ値を計算（odds_1, odds_2の大きい方）
odds_3rentan = odds[odds["bet_code"] == 5].copy()
odds_3rentan["odds"] = odds_3rentan[["odds_1", "odds_2"]].max(axis=1)

# レースごとの最大オッズを取得
odds_max = odds_3rentan.groupby(["date", "venue_id", "race_no"])["odds"].max().reset_index(name="odds_max")

# レースごとの出走人数を取得
num_racers = results.groupby(["date", "venue_id", "race_no"])["racer_id"].count().reset_index(name="num_racers")

# マージして is_arare フラグを定義
merged = pd.merge(odds_max, num_racers, on=["date", "venue_id", "race_no"], how="inner")
merged["is_arare"] = ((merged["odds_max"] >= 300) & (merged["num_racers"] == 9)).astype(int)

# 保存処理
os.makedirs(os.path.dirname(output_path), exist_ok=True)
merged.to_csv(output_path, index=False)
print(f"✅ is_arare ラベルを生成・保存しました: {output_path}")