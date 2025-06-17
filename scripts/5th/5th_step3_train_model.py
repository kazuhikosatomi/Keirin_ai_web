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

TRAIN_FILE = Path("data/5th/tmp/step2_train_racer_level.csv")
LABEL_FILE = Path("data/5th/step0_arare_labels_merged.csv")
MODEL_PATH = Path("data/5th/tmp/step3_arare_model.pkl")

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

# rankを数値化（"1"〜"9"のみをint化し、それ以外はNaN）
def parse_rank(val):
    try:
        return int(val)
    except:
        return None

if "rank" in df.columns:
    df["rank"] = df["rank"].apply(parse_rank)

# 欠損除去
required_cols = ["is_arare", "racer_id", "races", "win_rate"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise KeyError(f"❌ 欠損カラム: {missing_cols} が step2 出力に存在しません")
df = df.dropna(subset=required_cols)

# カテゴリ変換
for col in ['grade', 'prefecture']:
    if col in df.columns:
        df[col] = df[col].astype(str).astype('category').cat.codes

# 特徴量と目的変数
drop_cols = ["is_arare", "date", "hit"] if "hit" in df.columns else ["is_arare", "date"]
X = df.drop(columns=drop_cols)
y = df["is_arare"]
feature_names = X.columns.tolist()

# LightGBM データセット
lgb_train = lgb.Dataset(X, label=y)

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