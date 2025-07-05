import pandas as pd
import joblib
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="対象日付 (例: 2020-01-01)")
args = parser.parse_args()
target_date = args.date

entry_path = f"data/1st/tmp/step4_entry_with_features.csv"
output_dir = Path("data/1st/step5")
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"step5_predicted_rank_{target_date}.csv"
model_path = f"data/1st/tmp/step3_rank_model.pkl"

entry_df = pd.read_csv(entry_path)

# マスタファイルを読み込んでマージ
player_master = pd.read_csv("data/master/player_master.csv")
entry_df = pd.merge(entry_df, player_master[["racer_id", "name_kanji"]], on="racer_id", how="left")

# name_kanji列をracer_idの直後に
cols = list(entry_df.columns)
if "racer_id" in cols and "name_kanji" in cols:
    ridx = cols.index("racer_id")
    cols.insert(ridx + 1, cols.pop(cols.index("name_kanji")))
    entry_df = entry_df[cols]

# モデル読み込み
model = joblib.load(model_path)

missing_cols = [col for col in model.feature_name() if col not in entry_df.columns]
if missing_cols:
    print(f"⚠️ 欠損しているカラム: {missing_cols}")

# 特徴量列
X = entry_df[model.feature_name()].copy()

for col in X.columns:
    if X[col].dtype == "object":
        X[col] = X[col].astype('category').cat.codes


# 予測実行
entry_df["predicted_score"] = model.predict(X)
entry_df = entry_df.sort_values(by=["date", "venue_id", "race_no", "predicted_score"], ascending=[True, True, True, True])
entry_df["predicted_rank"] = entry_df.groupby(["date", "venue_id", "race_no"]).cumcount() + 1

# カラム順調整
cols = list(entry_df.columns)
for key in ["date", "venue_id", "race_no"]:
    cols.remove(key)
cols = ["date", "venue_id", "race_no"] + cols

if "car_no" in cols and "predicted_rank" in cols:
    cidx = cols.index("car_no")
    cols.remove("predicted_rank")
    cols.insert(cidx + 1, "predicted_rank")

entry_df = entry_df[cols]

# 出力保存
entry_df.to_csv(output_path, index=False)
print(f"📤 上書き保存: {output_path}")