import pandas as pd
import joblib
from pandas.api.types import CategoricalDtype

entry_df = pd.read_csv("data/2nd/entry_like_2020-01-01.csv")
# マスタファイルを読み込んでマージ
player_master = pd.read_csv("data/master/player_master.csv")
entry_df = pd.merge(entry_df, player_master[["racer_id", "name_kanji"]], on="racer_id", how="left")
# name_kanji列をracer_idの直後に
cols = list(entry_df.columns)
if "racer_id" in cols and "name_kanji" in cols:
    ridx = cols.index("racer_id")
    cols.insert(ridx + 1, cols.pop(cols.index("name_kanji")))
    entry_df = entry_df[cols]
model = joblib.load("models/2nd/rank_model_2015_2019.pkl")

# 特徴量列（model.feature_name() で取得）
X = entry_df[model.feature_name()].copy()

# 数値ID化（学習時と同様に category → cat.codes）
for col in ["grade", "prefecture", "venue_id"]:
    if col in X.columns:
        X[col] = X[col].astype('category').cat.codes

# ✅ 予測実行
entry_df["predicted_score"] = model.predict(X)
entry_df = entry_df.sort_values(by=["date", "venue_id", "race_no", "predicted_score"], ascending=[True, True, True, True])
entry_df["predicted_rank"] = entry_df.groupby(["date", "venue_id", "race_no"]).cumcount() + 1

# カラム順を調整
cols = list(entry_df.columns)
for key in ["date", "venue_id", "race_no"]:
    cols.remove(key)
cols = ["date", "venue_id", "race_no"] + cols

if "car_no" in cols and "predicted_rank" in cols:
    cidx = cols.index("car_no")
    cols.remove("predicted_rank")
    cols.insert(cidx + 1, "predicted_rank")

entry_df = entry_df[cols]

# ✅ 出力保存
entry_df.to_csv("data/2nd/predicted_rank_2020-01-01.csv", index=False)
print("✅ 予測結果を保存しました: data/2nd/predicted_rank_2020-01-01.csv")