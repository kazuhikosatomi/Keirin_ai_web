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
TRAIN_FILE = Path("data/1st/tmp/step2_train_racer_level.csv")
MODEL_PATH = Path("data/1st/tmp/step3_rank_model.pkl")

# 読み込み
df = pd.read_csv(TRAIN_FILE, low_memory=False)
# print(f"✅ データ読み込み完了: {TRAIN_FILE}")
# print(f"📊 レコード数: {len(df)}")
# print(f"📋 カラム一覧: {list(df.columns)}")

# 欠損確認
# print("🧪 欠損のあるカラム:")
# print(df.isna().sum()[df.isna().sum() > 0])

# 欠損行除外（最低限）
df = df.dropna(subset=["rank", "racer_id", "races", "win_rate"])

# カテゴリを数値ID化（文字列であっても安全に変換）
for col in ['grade', 'prefecture', 'prefecture_x', 'prefecture_y', 'area', 'group']:
    if col in df.columns:
        df[col] = df[col].astype(str).astype('category').cat.codes

# rank列をfloatに変換
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

# rankカラムがない場合はエラー
if "rank" not in df.columns:
    raise ValueError("❌ 'rank' カラムが存在しません。目的変数が必要です。")

# 特徴量と目的変数の分離
drop_cols = ["rank", "date", "hit"] if "hit" in df.columns else ["rank", "date"]
X = df.drop(columns=drop_cols)
# print(f"✅ 特徴量カラム一覧: {X.columns.tolist()}")
y = df["rank"]
if "hit" in df.columns:
    print("✅ 'hit' カラムを特徴量として使用します")
feature_names = X.columns.tolist()
# print("📊 特徴量カラム一覧:", feature_names)

# LightGBM データセット化
lgb_train = lgb.Dataset(X, label=y)

# モデル学習
params = {
    "objective": "regression",
    "metric": "rmse",
    "verbosity": -1,
}
model = lgb.train(params, lgb_train, num_boost_round=100)

# 保存
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(model, MODEL_PATH)
print(f"📤 上書き保存: {MODEL_PATH}")

# 特徴量重要度の取得と表示
import matplotlib.pyplot as plt

importance = model.feature_importance()
feature_names = model.feature_name()

importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': importance
}).sort_values(by='importance', ascending=False)

# 表示
print("📊 特徴量の重要度（上位）:")
print(importance_df.head(10))

# 特定の特徴量に注目（line_idとline_pos）
target_features = ["line_id", "line_pos"]
print("🔍 line_id / line_pos の重要度:")
print(importance_df[importance_df["feature"].isin(target_features)])

# CSVで保存
importance_df.to_csv("data/1st/tmp/step3_feature_importance.csv", index=False)

# 重要度グラフ（任意）
plt.figure(figsize=(10, 6))
lgb.plot_importance(model, max_num_features=20)
plt.tight_layout()
plt.savefig("data/1st/tmp/step3_feature_importance.png")
plt.close()

# 相関係数分析の追加
print("\n📊 特徴量間の相関係数（上位）:")
correlation_matrix = pd.concat([X, y], axis=1).corr()
target_corr = correlation_matrix["rank"].drop("rank").abs().sort_values(ascending=False)
print(target_corr.head(10))