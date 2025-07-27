import pandas as pd
import lightgbm as lgb
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

# 入出力パス
# 未来の出走表（対象日）のみを対象とする
input_path = Path(f"data/8th/tmp/step3_entry_features.csv")
model_path = Path("data/8th/tmp/step2_arare_race_model.txt")
feature_list_path = "data/8th/tmp/step2_arare_feature_list.txt"
pkl_model_path = "data/8th/tmp/step2_arare_race_model.pkl"
output_path = Path(f"data/8th/step4/predictions_{target_date}.csv")

# データ読み込み
df = pd.read_csv(input_path)

# 🔍 object型のカラムを事前にチェックして出力
object_cols = df.select_dtypes(include="object").columns.tolist()
if object_cols:
    print(f"⚠️ object型カラムが検出されました（自動除外対象）: {object_cols}")
else:
    print("✅ object型カラムは存在しません")

if 'race_grade_encoded' not in df.columns:
    print("⚠️ 'race_grade_encoded' が存在しません。step3での出力を確認してください。")

# LightGBMが嫌う object 型の列は除外しておく
df = df.drop(columns=[col for col in df.columns if df[col].dtype == "object"])

# 特徴量リストを読み込み
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
with open(pkl_model_path, "rb") as f:
    model = pickle.load(f)

# 予測
df["predicted_score"] = model.predict(df[features])
df["predicted_score"] = df["predicted_score"].round(3)

# 'date' カラムが存在しない場合は補完（対象日 と仮定）
if "date" not in df.columns:
    df["date"] = target_date

# 出力
output_path.parent.mkdir(parents=True, exist_ok=True)
df[["date", "venue_id", "race_no", "predicted_score"]].to_csv(output_path, index=False, float_format="%.3f")
print(f"✅ 出力完了: {output_path}")