import pandas as pd
from pathlib import Path

# 入力ファイルパス
label_path = Path("data/7th/step0_arare_labels_merged.csv")
features_path = Path("data/7th/tmp/step1_race_features.csv")

# 出力ファイルパス
output_path = Path("data/7th/tmp/step2_merged.csv")

# データ読み込み
df_label = pd.read_csv(label_path)
df_feat = pd.read_csv(features_path)

# 結合キー
merge_keys = ["date", "venue_id", "race_no"]

# マージ実行（内部結合）
df_merged = pd.merge(df_feat, df_label, on=merge_keys, how="inner")

# 欠損のある行を除去（必要なら）
df_merged = df_merged.dropna()

# 出力
output_path.parent.mkdir(parents=True, exist_ok=True)
df_merged.to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")