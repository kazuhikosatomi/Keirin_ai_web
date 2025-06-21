import pandas as pd
import lightgbm as lgb
from pathlib import Path

# 入出力パス
input_path = Path("data/7th/step3_train_race_level.csv")
model_path = Path("models/7th/arare_race_model.txt")
output_path = Path("data/7th/step5_predictions.csv")

# データ読み込み
df = pd.read_csv(input_path)
df["roof_type_encoded"] = df["roof_type"].map({"ドーム": 1, "屋外": 0})
features = [col for col in df.columns if col not in ["date", "venue_id", "race_no", "is_arare", "roof_type"]]

# モデル読み込み
model = lgb.Booster(model_file=str(model_path))

# 予測
df["predicted_score"] = model.predict(df[features])
df["predicted_score"] = df["predicted_score"].round(3)

# 出力
df[["date", "venue_id", "race_no", "predicted_score"]].to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")