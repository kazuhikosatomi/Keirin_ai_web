import pandas as pd
import lightgbm as lgb
from pathlib import Path

# 入出力パス
# 未来の出走表（2025-01-01）のみを対象とする
input_path = Path("data/7th/entry_2025-06-22_with_features.csv")
model_path = Path("models/7th/arare_race_model.txt")
output_path = Path("data/7th/step5_predictions.csv")

# データ読み込み
df = pd.read_csv(input_path)

# 🔍 object型のカラムを事前にチェックして出力
object_cols = df.select_dtypes(include="object").columns.tolist()
if object_cols:
    print(f"⚠️ object型カラムが検出されました（自動除外対象）: {object_cols}")
else:
    print("✅ object型カラムは存在しません")

# LightGBMが嫌う object 型の列は除外しておく
df = df.drop(columns=[col for col in df.columns if df[col].dtype == "object"])

# 特徴量リストを読み込み
feature_list_path = "models/7th/arare_feature_list.txt"
with open(feature_list_path) as f:
    raw_features = [line.strip() for line in f]

# 特徴量の順序と数を完全一致させる
features = [line.strip() for line in raw_features]

# 欠損カラムをチェック（厳密な整合性チェック）
missing_cols = [col for col in features if col not in df.columns]
if missing_cols:
    raise ValueError(f"💥 以下の特徴量が df に存在しません: {missing_cols}")

# モデル読み込み（pkl形式）
import pickle
with open("models/7th/arare_race_model.pkl", "rb") as f:
    model = pickle.load(f)

# 予測
df["predicted_score"] = model.predict(df[features])
df["predicted_score"] = df["predicted_score"].round(3)

# 'date' カラムが存在しない場合は補完（2025-01-01 と仮定）
if "date" not in df.columns:
    df["date"] = "2025-01-01"

# 出力
df[["date", "venue_id", "race_no", "predicted_score"]].to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")