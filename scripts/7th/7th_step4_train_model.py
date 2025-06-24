import pandas as pd
import lightgbm as lgb
import os

# 入出力パス
input_path = "data/7th/tmp/step3_train_race_level.csv"
model_path = "data/7th/tmp/step4_arare_race_model.txt"
feature_importance_path = "data/7th/tmp/step4_feature_importance.csv"

# データ読み込み
df = pd.read_csv(input_path)

if "roof_type" in df.columns:
    df["roof_type"] = df["roof_type"].astype("category").cat.codes

# 特徴量と目的変数（object型・roof_typeなど不要なものは除外）
target_col = "is_arare"
exclude_cols = ["date", "venue_id", "race_no", target_col, "roof_type"]
feature_cols = [col for col in df.columns if col not in exclude_cols and df[col].dtype in ["int64", "float64", "bool"]]

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
pkl_model_path = "data/7th/tmp/step4_arare_race_model.pkl"
os.makedirs(os.path.dirname(pkl_model_path), exist_ok=True)
with open(pkl_model_path, "wb") as f:
    pickle.dump(model, f)
print(f"💾 Pickle形式でモデル保存完了: {pkl_model_path}")

# 使用した特徴量を保存
feature_list_path = "data/7th/tmp/step4_arare_feature_list.txt"
os.makedirs(os.path.dirname(feature_list_path), exist_ok=True)
with open(feature_list_path, "w") as f:
    for col in feature_cols:
        f.write(col + "\n")
print(f"📝 使用特徴量リストを保存: {feature_list_path}")

# 除外カラムと使用カラムの一覧を表示
print("\n🟥 除外カラム（exclude_cols）:")
for col in exclude_cols:
    print(" -", col)

print("\n🟩 使用カラム（feature_cols）:")
for col in feature_cols:
    print(" +", col)