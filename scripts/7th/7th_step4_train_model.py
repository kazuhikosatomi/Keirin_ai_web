import pandas as pd
import lightgbm as lgb
import os

# 入出力パス
input_path = "data/7th/step3_train_race_level.csv"
model_path = "models/7th/arare_race_model.txt"
feature_importance_path = "data/7th/step4_feature_importance.csv"

# データ読み込み
df = pd.read_csv(input_path)

if "roof_type" in df.columns:
    df["roof_type"] = df["roof_type"].astype("category").cat.codes

# 特徴量と目的変数
target_col = "is_arare"
feature_cols = [col for col in df.columns if col not in ["date", "venue_id", "race_no", target_col]]

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
    "scale_pos_weight": 100
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