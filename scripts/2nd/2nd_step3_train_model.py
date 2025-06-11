import pandas as pd
import lightgbm as lgb
from pathlib import Path
import joblib

# 入力ファイル
TRAIN_FILE = Path("data/2nd/train_racer_level_2015_2019.csv")
MODEL_PATH = Path("models/2nd/rank_model_2015_2019.pkl")

# 読み込み
df = pd.read_csv(TRAIN_FILE)
print(f"✅ データ読み込み完了: {TRAIN_FILE}")
print(f"📊 レコード数: {len(df)}")
print(f"📋 カラム一覧: {list(df.columns)}")

# 欠損確認
print("🧪 欠損のあるカラム:")
print(df.isna().sum()[df.isna().sum() > 0])

# 欠損行除外（最低限）
df = df.dropna(subset=["rank", "racer_id", "races", "win_rate"])

# カテゴリを数値ID化（文字列であっても安全に変換）
for col in ['grade', 'prefecture']:
    if col in df.columns:
        df[col] = df[col].astype(str).astype('category').cat.codes

# rank列をfloatに変換
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

# rankカラムがない場合はエラー
if "rank" not in df.columns:
    raise ValueError("❌ 'rank' カラムが存在しません。目的変数が必要です。")

# 特徴量と目的変数の分離
X = df.drop(columns=["rank", "date"])
y = df["rank"]

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
print(f"✅ モデル保存完了: {MODEL_PATH}")