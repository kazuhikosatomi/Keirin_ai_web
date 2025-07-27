import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="基準日 (例: 2025-01-02)")
args = parser.parse_args()
base_date = datetime.strptime(args.date, "%Y-%m-%d")
prev_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")

input_path = "data/arare/arare2_merged.csv"
output_path = "data/8th/tmp/step1_train_data.csv"

# データ読み込み
df = pd.read_csv(input_path)

# フィードバックファイルを読み込んで結合（あれば）
if prev_date:
    feedback_path = Path(f"data/8th/step6/feedback_{prev_date}.csv")
    if feedback_path.exists():
        print(f"🔁 前日フィードバック読み込み: {feedback_path}")
        feedback_df = pd.read_csv(feedback_path)

        # フィードバックに含める有効なカラムのみ抽出（予測由来のものは除外）
        valid_cols = [
            'date', 'venue_id', 'race_no', 'num_racers', 'avg_age', 'num_lines',
            'line_size_std', 'num_solo', 'venue_length', 'straight_length',
            'has_cross_area_line', 'max_line_size', 'age_std', 'score_std',
            'score_max', 'score_min', 'escape_max', 'sprint_max', 'is_arare'
        ]
        feedback_df = feedback_df[[col for col in feedback_df.columns if col in valid_cols]]
        print(f"✅ フィードバックから {len(feedback_df)} 件の有効レコードを抽出")
        df = pd.concat([df, feedback_df], ignore_index=True)
    else:
        print(f"⚠️ フィードバックファイルなし: {feedback_path}")

# メタ情報・目的変数のカラム
meta_cols = ["date", "venue_id", "race_no"]
target_col = "is_arare"

# 特徴量となるカラム（metaと目的変数以外）
feature_cols = [col for col in df.columns if col not in meta_cols + [target_col]]
if "odds" in feature_cols:
    feature_cols.remove("odds")

# car_1〜car_3 を除外（車番番号が予測ラベルと関係する恐れがあるため）
for col in ["car_1", "car_2", "car_3"]:
    if col in feature_cols:
        feature_cols.remove(col)

# カラム順を整理して保存
df_out = df[meta_cols + feature_cols + [target_col]]
os.makedirs(os.path.dirname(output_path), exist_ok=True)
# データを保存
df_out.to_csv(output_path, index=False)

print(f"✅ 出力完了: {output_path}")