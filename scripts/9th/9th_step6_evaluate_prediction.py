import pandas as pd
import argparse
import os
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="予測対象日（例: 2023-01-01）")
args = parser.parse_args()
target_date = args.date

# ログ: START
print(f"🚀 [START] 9th_step6_evaluate_prediction.py target_date={target_date}")

# 9th_step6_evaluate_prediction.py

# 🔹 予測スコア読み込み（選手単位）
pred_path = f"data/9th/step5c/step5c_predictions_ranked_{target_date}.csv"
pred_df = pd.read_csv(pred_path)
print(f"📊 予測読込: {len(pred_df)} 行 from {pred_path}")

# 🔹 レース単位の最大スコア（または平均でも可）を使用
score_df = pred_df.groupby(["date", "venue_id", "race_no"])["arare_score_combined"].max().reset_index()
score_df = score_df.rename(columns={"arare_score_combined": "arare_score"})
print(f"📊 レース集約: {len(score_df)} レース")

# 🔹 着順データを取得（正解ラベル）
results_df = pd.read_csv(f"data/results/{target_date[:4]}/results_{target_date}.csv")
print(f"📊 結果読込: {len(results_df)} 行")

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
print(f"📊 オッズ(3連単)読込: {len(odds_trio)} 行")

# 🔹 実際の的中オッズをマージ
merged = pd.merge(combo_df, odds_trio, on=["date", "venue_id", "race_no", "car_1", "car_2", "car_3"], how="left")
print(f"📊 正解オッズ結合: {len(merged)} 行")

# 🔹 荒れ判定
merged["actual_odds"] = merged["odds_1"]
merged["is_arare"] = (merged["actual_odds"] >= 300).astype(int)

# 🔹 予測スコアと結合
eval_df = pd.merge(score_df, merged[["date", "venue_id", "race_no", "actual_odds", "is_arare"]], on=["date", "venue_id", "race_no"], how="inner")
print(f"📊 評価用結合: {len(eval_df)} 行")

# 🔹 相関係数
corr = eval_df["arare_score"].corr(eval_df["is_arare"])
print(f"📊 相関係数（arare_score vs is_arare）: {corr:.4f}")

# 🔹 ROC-AUC
roc_auc = roc_auc_score(eval_df["is_arare"], eval_df["arare_score"])
print(f"📊 ROC-AUC（arare_score vs is_arare）: {roc_auc:.4f}")

# 🔹 しきい値0.5での予測
arare_pred = (eval_df["arare_score"] >= 0.5).astype(int)
acc = accuracy_score(eval_df["is_arare"], arare_pred)
precision = precision_score(eval_df["is_arare"], arare_pred, zero_division=0)
recall = recall_score(eval_df["is_arare"], arare_pred, zero_division=0)
f1 = f1_score(eval_df["is_arare"], arare_pred, zero_division=0)
print(f"📊 正解率（accuracy, しきい値0.5）: {acc:.4f}")
print(f"📊 適合率（precision, しきい値0.5）: {precision:.4f}")
print(f"📊 再現率（recall, しきい値0.5）: {recall:.4f}")
print(f"📊 F1スコア（しきい値0.5）: {f1:.4f}")

# 🔹 保存
os.makedirs("data/9th/step6", exist_ok=True)
output_path = f"data/9th/step6/step6_evaluation_arare_{target_date}.csv"
eval_df.to_csv(output_path, index=False)
print(f"💾 保存完了: {output_path}")
print("🏁 [END] 9th_step6_evaluate_prediction.py")