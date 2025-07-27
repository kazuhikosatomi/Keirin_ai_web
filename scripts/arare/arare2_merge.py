import pandas as pd
from pathlib import Path
import argparse
from datetime import datetime

# 入力ファイルパス
label_path = Path("data/arare/arare0_arare_labels.csv")
features_path = Path("data/arare/arare1_race_stats.csv")


# 引数パース
parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()
base_date = args.date

# 出力ファイルパス
output_path = Path("data/arare/arare2_merged.csv")

# データ読み込み
df_label = pd.read_csv(label_path)
df_feat = pd.read_csv(features_path)

# 結合キー
merge_keys = ["date", "venue_id", "race_no"]

# マージ実行（内部結合）
df_merged = pd.merge(df_feat, df_label, on=merge_keys, how="inner")

# 欠損のある行を除去（必要なら）
df_merged = df_merged.dropna()

# 出力
output_path.parent.mkdir(parents=True, exist_ok=True)
df_merged.to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")