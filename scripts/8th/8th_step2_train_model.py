import pandas as pd
import lightgbm as lgb
import os
import argparse
from datetime import datetime
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="基準日 (例: 2025-01-02)")
args = parser.parse_args()
base_date = args.date

# 入出力パス
input_path = "data/8th/tmp/step1_train_data.csv"
model_path = "data/8th/tmp/step2_arare_race_model.txt"
feature_importance_path = "data/8th/tmp/step2_feature_importance.csv"

# データ読み込み
df = pd.read_csv(input_path)

# object型 'race_grade' を数値化（新たに race_grade_encoded を追加）
if 'race_grade' in df.columns:
    df['race_grade_encoded'] = df['race_grade'].astype('category').cat.codes

# 型変換（カテゴリ変数や bool に変換）
if "roof_type" in df.columns:
    df["roof_type"] = df["roof_type"].astype("category").cat.codes

if "has_cross_area_line" in df.columns:
    df["has_cross_area_line"] = df["has_cross_area_line"] == True  # 確実に bool 型に変換

# 特徴量と目的変数（object型・roof_typeなど不要なものは除外）
target_col = "is_arare"
exclude_cols = [col for col in ["date", "venue_id", "race_no", target_col, "roof_type"] if col in df.columns]

# 特徴量抽出: int, float, bool 型を含める
feature_cols = [
    'num_lines', 'num_solo', 'avg_line_size', 'std_line_size', 'max_line_size',
    'leader_count', 'group_diversity', 'has_cross_area_line', 'num_racers',
    'num_SS', 'num_S1', 'num_S2', 'num_A1', 'num_A2', 'num_A3', 'num_L1',
    'age_std', 'avg_top3_rate', 'std_top3_rate', 'avg_top2_rate', 'std_top2_rate',
    'avg_win_rate', 'std_win_rate', 'score_std', 'score_max', 'score_min',
    'escape_max', 'sprint_max',
    'race_grade_encoded'  # ←追加
]

X = df[feature_cols]
y = df[target_col]

# LightGBM 用データセット
lgb_train = lgb.Dataset(X, y)

# パラメータ設定（シンプル）
params = {
    "objective": "binary",
    "metric": "binary_logloss",
    "verbosity": -1,
    "seed": 42,
    "scale_pos_weight": 9
}

# 学習
model = lgb.train(params, lgb_train)

# 保存
os.makedirs(os.path.dirname(model_path), exist_ok=True)
model.save_model(model_path)
print(f"✅ モデル保存完了: {model_path}")

# 特徴量重要度を出力
importance_df = pd.DataFrame({
    "feature": feature_cols,
    "importance": model.feature_importance()
}).sort_values("importance", ascending=False)

importance_df.to_csv(feature_importance_path, index=False)
print(f"📊 特徴量重要度を保存: {feature_importance_path}")

# Pickle形式でも保存（再利用や予測に便利）
import pickle
pkl_model_path = "data/8th/tmp/step2_arare_race_model.pkl"
os.makedirs(os.path.dirname(pkl_model_path), exist_ok=True)
with open(pkl_model_path, "wb") as f:
    pickle.dump(model, f)
print(f"💾 Pickle形式でモデル保存完了: {pkl_model_path}")

# 使用した特徴量を保存
feature_list_path = "data/8th/tmp/step2_arare_feature_list.txt"
os.makedirs(os.path.dirname(feature_list_path), exist_ok=True)
with open(feature_list_path, "w") as f:
    for col in feature_cols:
        f.write(col + "\n")
print(f"📝 使用特徴量リストを保存: {feature_list_path}")

# 除外カラムと使用カラムの一覧を表示
#print("\n🟥 除外カラム（exclude_cols）:")
#for col in exclude_cols:
#    print(" -", col)

#print("\n🟩 使用カラム（feature_cols）:")
#for col in feature_cols:
#    print(" +", col)