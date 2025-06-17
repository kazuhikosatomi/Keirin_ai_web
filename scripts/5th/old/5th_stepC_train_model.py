import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, roc_auc_score
import os
import joblib

# 🔹 データ読み込み
df = pd.read_csv("data/5th/stepB_train_entry_like.csv")

# 🔧 不正データの型変換
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
df["grade"] = df["grade"].astype("category").cat.codes

# 🔹 特徴量と目的変数の指定
target_col = "label"
exclude_cols = ["date", "venue_id", "race_no", "car_no", "racer_id", "label"]
feature_cols = [col for col in df.columns if col not in exclude_cols]

X = df[feature_cols]
y = df[target_col]

# 🔹 学習データと検証データに分割
X_train, X_valid, y_train, y_valid = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 🔹 LightGBM 用データセットに変換
lgb_train = lgb.Dataset(X_train, y_train)
lgb_valid = lgb.Dataset(X_valid, y_valid, reference=lgb_train)

# 🔹 ハイパーパラメータ設定
params = {
    "objective": "binary",
    "metric": ["binary_logloss", "auc"],
    "verbosity": -1,
    "boosting_type": "gbdt",
    "seed": 42,
}

# 🔹 学習実行
model = lgb.train(
    params,
    lgb_train,
    valid_sets=[lgb_train, lgb_valid],
    num_boost_round=1000,
    callbacks=[
        lgb.early_stopping(50),
        lgb.log_evaluation(100)
    ],
)

# 🔹 モデル保存
os.makedirs("data/5th", exist_ok=True)
model.save_model("data/5th/stepC_lgbm_model.txt")
import joblib
joblib.dump(model, "data/5th/stepC_lgbm_model.pkl")

# 🔹 評価表示
y_pred_prob = model.predict(X_valid)
print(f"log_loss: {log_loss(y_valid, y_pred_prob):.4f}")
print(f"auc: {roc_auc_score(y_valid, y_pred_prob):.4f}")

print(f"✅ 学習完了: {len(df)} 件 → data/5th/stepC_model.pkl")