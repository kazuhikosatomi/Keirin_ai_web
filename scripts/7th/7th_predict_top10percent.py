import pandas as pd
import os

# 入力ファイルと出力ファイルのパス
input_path = "data/7th/step5_predictions.csv"
output_path = "data/7th/step6_ranked_predictions.csv"

# ファイル読み込み
df = pd.read_csv(input_path)

# スコア上位10%の閾値を計算
threshold = df["predicted_score"].quantile(0.9)

# 閾値以上を is_arare=1 と判定
df["predicted_is_arare"] = (df["predicted_score"] >= threshold).astype(int)

# スコア順にソートして保存
df.sort_values("predicted_score", ascending=False).to_csv(output_path, index=False)

print(f"✅ 上位10%を is_arare=1 として保存しました: {output_path}")
print(f"🔎 スコア閾値: {threshold:.8f}")