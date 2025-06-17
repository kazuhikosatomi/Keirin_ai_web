import pandas as pd
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="予測対象日（例: 2023-01-01）")
args = parser.parse_args()
target_date = args.date

# 🔹 予測スコア読み込み（選手単位）
pred_df = pd.read_csv("data/5th/tmp/step5_arare_predictions.csv")

# 🔹 レース単位の最大スコア（または平均でも可）を使用
score_df = pred_df.groupby(["date", "venue_id", "race_no"])["arare_score"].max().reset_index()

# 🔹 着順データを取得（正解ラベル）
results_df = pd.read_csv(f"data/results/{target_date[:4]}/results_{target_date}.csv")

# 1〜3着のcar_noを抽出してセットとして結合（順番付き）
top3_df = results_df[results_df["rank"].isin(["1", "2", "3"])]
top3_sorted = top3_df.sort_values(["date", "venue_id", "race_no", "rank"])
combo_df = top3_sorted.groupby(["date", "venue_id", "race_no"])["car_no"].apply(list).reset_index()
combo_df = combo_df[combo_df["car_no"].apply(len) == 3]
combo_df[["car_1", "car_2", "car_3"]] = pd.DataFrame(combo_df["car_no"].tolist(), index=combo_df.index)
combo_df.drop(columns=["car_no"], inplace=True)

# 🔹 オッズ（3連単）読み込み
odds_df = pd.read_csv(f"data/odds/{target_date[:4]}/odds_{target_date}.csv")
odds_trio = odds_df.query("bet_code == 5").copy()

# 🔹 実際の的中オッズをマージ
merged = pd.merge(combo_df, odds_trio, on=["date", "venue_id", "race_no", "car_1", "car_2", "car_3"], how="left")

# 🔹 荒れ判定
merged["actual_odds"] = merged["odds_1"]
merged["is_arare"] = (merged["actual_odds"] >= 300).astype(int)

# 🔹 予測スコアと結合
eval_df = pd.merge(score_df, merged[["date", "venue_id", "race_no", "actual_odds", "is_arare"]], on=["date", "venue_id", "race_no"], how="inner")

# 🔹 相関係数
corr = eval_df["arare_score"].corr(eval_df["is_arare"])
print(f"📊 相関係数（arare_score vs is_arare）: {corr:.4f}")

# 🔹 保存
os.makedirs("data/5th/step6", exist_ok=True)
output_path = f"data/5th/step6/step6_evaluation_arare_{target_date}.csv"
eval_df.to_csv(output_path, index=False)
print(f"📤 保存完了: {output_path}")