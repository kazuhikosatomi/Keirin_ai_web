import pandas as pd
import os
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

# 入出力パス
input_path = f"data/entries/{target_date[:4]}/entry_{target_date}.csv"
output_path = "data/7th/tmp/step5_1_entry_with_features.csv"

# 読み込み
df = pd.read_csv(input_path)

# venue_master から roof_type を補完
venue_master = pd.read_csv("data/master/venue_master.csv")
df = df.merge(venue_master[["venue_id", "roof_type"]], on="venue_id", how="left")
df["roof_type_encoded"] = df["roof_type"].map({"ドーム": 1, "屋外": 0}).fillna(0).astype(int)

# 年齢統計量
if "age" in df.columns:
    df["avg_age"] = df.groupby(["date", "venue_id", "race_no"])["age"].transform("mean")
    df["age_std"] = df.groupby(["date", "venue_id", "race_no"])["age"].transform("std").fillna(0)
else:
    df["avg_age"] = 0
    df["age_std"] = 0

# group（ライン）関連
if "line_id" in df.columns and "race_no" in df.columns:
    group_counts = df["line_id"].value_counts()
    df["line_size"] = df["line_id"].map(group_counts)
    df["line_size_std"] = df.groupby(["date", "venue_id", "race_no"])["line_size"].transform("std").fillna(0)
    df["num_lines"] = df.groupby(["date", "venue_id", "race_no"])["line_id"].transform("nunique")
    df["num_solo"] = df["line_id"].map(lambda x: 1 if pd.notna(x) and group_counts.get(x, 0) == 1 else 0)
else:
    df["line_size_std"] = 0
    df["num_lines"] = 0
    df["num_solo"] = 0

# 仮スコア（予測前のプレースホルダ）
df["score"] = 0.0
df["score_min"] = df.groupby(["date", "venue_id", "race_no"])["score"].transform("min")
df["score_max"] = df.groupby(["date", "venue_id", "race_no"])["score"].transform("max")
df["score_std"] = df.groupby(["date", "venue_id", "race_no"])["score"].transform("std").fillna(0)

# 正しいカラム名に合わせて venue_master から補完
df = df.merge(
    venue_master[["venue_id", "track_length_m", "virtual_straight_m"]]
    .rename(columns={"track_length_m": "venue_length", "virtual_straight_m": "straight_length"}),
    on="venue_id", how="left"
)

# 出走人数
df["num_racers"] = df.groupby(["date", "venue_id", "race_no"])["racer_id"].transform("count")

# 最大ラインサイズ
if "line_id" in df.columns:
    df["max_line_size"] = df.groupby(["date", "venue_id", "race_no"])["line_size"].transform("max")
else:
    df["max_line_size"] = 0

# 地区横断ラインの有無（race_no内で複数地区を持つline_idがあるか）
if "area_id" in df.columns and "line_id" in df.columns:
    def check_cross_area(group):
        return int(group.groupby("line_id")["area_id"].nunique().max() > 1 if group["line_id"].notna().any() else 0)
    df["has_cross_area_line"] = df.groupby(["date", "venue_id", "race_no"]).apply(check_cross_area).reindex(df.index).values
else:
    df["has_cross_area_line"] = 0

# 最大 escape/sprint スコア（仮に存在するとして処理）
if "style_escape" in df.columns:
    df["escape_max"] = df.groupby(["date", "venue_id", "race_no"])["style_escape"].transform("max")
else:
    df["escape_max"] = 0
if "style_sprint" in df.columns:
    df["sprint_max"] = df.groupby(["date", "venue_id", "race_no"])["style_sprint"].transform("max")
else:
    df["sprint_max"] = 0

# レース単位に集約して出力（平均など）
race_df = df.groupby(["date", "venue_id", "race_no"], as_index=False).mean(numeric_only=True)

# 保存
os.makedirs(os.path.dirname(output_path), exist_ok=True)
race_df.to_csv(output_path, index=False)
print("✅ 特徴量を（レース単位で）追加して保存しました: data/7th/tmp/step5_1_entry_with_features.csv")