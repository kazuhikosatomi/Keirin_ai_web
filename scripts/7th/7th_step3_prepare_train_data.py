import pandas as pd

input_path = "data/7th/step2_merged.csv"
output_path = "data/7th/step3_train_race_level.csv"

# データ読み込み
df = pd.read_csv(input_path)

# メタ情報・目的変数のカラム
meta_cols = ["date", "venue_id", "race_no"]
target_col = "is_arare"

# 特徴量となるカラム（metaと目的変数以外）
feature_cols = [col for col in df.columns if col not in meta_cols + [target_col]]

# カラム順を整理して保存
df_out = df[meta_cols + feature_cols + [target_col]]
df_out.to_csv(output_path, index=False)

print(f"✅ 出力完了: {output_path}")