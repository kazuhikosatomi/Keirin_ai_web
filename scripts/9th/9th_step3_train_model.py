import argparse
from datetime import datetime
import pandas as pd
import lightgbm as lgb
from pathlib import Path
import joblib

parser = argparse.ArgumentParser()
parser.add_argument('--date', required=True)
args = parser.parse_args()
dt = datetime.strptime(args.date, "%Y-%m-%d")

TRAIN_FILE = Path("data/9th/tmp/step2_train_data.csv")
LABEL_FILE = Path("data/arare/arare2_merged.csv")
MODEL_PATH = Path("data/9th/tmp/step3_arare_model.pkl")

# 読み込み
df = pd.read_csv(TRAIN_FILE)
labels = pd.read_csv(LABEL_FILE)

# is_arare が既に存在しない場合のみマージ
if "is_arare" not in df.columns:
    labels = labels.rename(columns={"label": "is_arare"})
    df = pd.merge(
        df,
        labels[["date", "venue_id", "race_no", "is_arare"]],
        on=["date", "venue_id", "race_no"],
        how="left"
    )
else:
    print("🔍 is_arare カラムはすでに存在するためマージをスキップ")


# 欠損除去
required_cols = ["is_arare", "racer_id", "races",
    "win_rate_G1", "win_rate_G2", "win_rate_G3", "win_rate_F1", "win_rate_F2",
    "top2_rate_G1", "top2_rate_G2", "top2_rate_G3", "top2_rate_F1", "top2_rate_F2",
    "top3_rate_G1", "top3_rate_G2", "top3_rate_G3", "top3_rate_F1", "top3_rate_F2"
]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise KeyError(f"❌ 欠損カラム: {missing_cols} が step2 出力に存在しません")
df = df.dropna(subset=required_cols)

# カテゴリ変換
categorical_cols = ["grade", "prefecture", "area", "group", "venue_id"]
for col in categorical_cols:
    if col in df.columns:
        df[col] = df[col].astype(str).astype('category').cat.codes

# 特徴量と目的変数
drop_cols = ["is_arare", "date", "rank", "hit"] if "hit" in df.columns else ["is_arare", "date", "rank"]
X = df.drop(columns=drop_cols)
y = df["is_arare"]
feature_names = X.columns.tolist()

 # LightGBM データセット
lgb_train = lgb.Dataset(X, label=y, categorical_feature=categorical_cols)

# モデル学習
params = {
    "objective": "binary",
    "metric": "auc",
    "verbosity": -1,
}
model = lgb.train(params, lgb_train, num_boost_round=100)

# 保存
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_PATH)
print(f"📤 上書き保存: {MODEL_PATH}")

# 特徴量の重要度を取得・表示・保存
importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": model.feature_importance()
}).sort_values(by="importance", ascending=False)

print("📊 特徴量の重要度（上位）:")
print(importance_df.head(10).to_string(index=False))

importance_df.to_csv("data/9th/tmp/step3_feature_importance.csv", index=False)