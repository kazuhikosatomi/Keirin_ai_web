# scripts/4th/check_feature_columns.py

import pandas as pd

# ファイルパス
train_file = "data/4th/tmp/step2_train_racer_level.csv"
entry_file = "data/4th/tmp/step4_entry_with_features.csv"

# CSV読み込み
train_df = pd.read_csv(train_file)
entry_df = pd.read_csv(entry_file)

# 特徴量（予測対象やIDなどを除いたカラム）を選定
exclude_cols = ['racer_id', 'date', 'car_no', 'rank', 'line_id', 'line_pos', 'hit', 'is_arare']
train_features = [col for col in train_df.columns if col not in exclude_cols]
entry_features = [col for col in entry_df.columns if col not in exclude_cols]

# 特徴量の差分チェック
train_only = sorted(set(train_features) - set(entry_features))
entry_only = sorted(set(entry_features) - set(train_features))
common = sorted(set(train_features) & set(entry_features))

# 結果表示
print("✅ 共通の特徴量:", len(common))
for col in common:
    print("  ┗", col)

print("\n📉 学習にのみ存在:", len(train_only))
for col in train_only:
    print("  ┗", col)

print("\n📈 予測にのみ存在:", len(entry_only))
for col in entry_only:
    print("  ┗", col)