import pandas as pd
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

# 入力ファイル
step5_path = Path(f"data/7th/tmp/step5_2_predictions_{target_date}.csv")
venue_path = Path("data/master/venue_master.csv")
output_path = Path(f"output/predict/csv/7th/final_prediction_arare_{target_date}.csv")

# 出力先ディレクトリ作成
output_path.parent.mkdir(parents=True, exist_ok=True)

# 読み込み
df = pd.read_csv(step5_path)
venue_master = pd.read_csv(venue_path)[["venue_id", "venue_name"]]

# マージ
df = pd.merge(df, venue_master, on="venue_id", how="left")

# カラム順の調整（venue_idの直後にvenue_nameを配置）
cols = df.columns.tolist()
if "venue_id" in cols and "venue_name" in cols:
    cols.remove("venue_name")
    venue_id_index = cols.index("venue_id") + 1
    cols.insert(venue_id_index, "venue_name")
    df = df[cols]

# 保存（必要な列のみ or 全体そのまま）
df.to_csv(output_path, index=False)
print(f"✅ 最終CSVを出力しました: {output_path}")