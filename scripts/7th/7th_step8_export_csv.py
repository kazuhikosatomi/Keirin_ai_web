import pandas as pd
import argparse
from pathlib import Path

# 🔹 引数：--date
parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True)
args = parser.parse_args()

# 🔹 入出力パス定義
base_dir = Path("data/7th/tmp")
output_dir = Path("output/predict/csv/7th")
output_dir.mkdir(parents=True, exist_ok=True)

pred_path = base_dir / "step5_2_predictions.csv"
venue_path = Path("data/master/venue_master.csv")

# 🔹 データ読み込み
df = pd.read_csv(pred_path)
venue_master = pd.read_csv(venue_path)

# 🔹 venue_name をマージ
df = pd.merge(df, venue_master[["venue_id", "venue_name"]], on="venue_id", how="left")

# 🔹 predict_score に変換し、元の predicted_score を削除し、順位を追加
df["predict_score"] = df["predicted_score"].fillna(0)
df.drop(columns=["predicted_score"], inplace=True)
df["predict_rank"] = df["predict_score"].rank(ascending=False, method="first").astype(int)

if "predict_score" in df.columns:
    df["predict_score"] = df["predict_score"].map(lambda x: f"{x:.3f}")

# 🔹 カラム順調整
cols = ["date", "venue_id", "venue_name", "race_no", "predict_score", "predict_rank"]
other_cols = [c for c in df.columns if c not in cols]
df = df[cols + other_cols]

# 🔹 出力
out_path = output_dir / f"final_prediction_arare_{args.date}.csv"
df.to_csv(out_path, index=False)
print(f"✅ 最終CSVを出力しました: {out_path}")