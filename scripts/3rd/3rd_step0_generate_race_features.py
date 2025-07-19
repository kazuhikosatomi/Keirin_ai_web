import pandas as pd
import argparse
from pathlib import Path

Path("data/3rd/tmp").mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()

base_date = pd.to_datetime(args.date) - pd.Timedelta(days=1)
start_date = base_date - pd.DateOffset(years=1)
date_list = pd.date_range(start=start_date, end=base_date).strftime("%Y-%m-%d").tolist()

master_path = Path("data/master/prefectures_master.csv")
all_features = []

for date in date_list:
    input_path = Path(f"data/results/{date[:4]}/results_{date}.csv")
    if not input_path.exists():
        print(f"⏭️ スキップ: {input_path}（ファイルなし）")
        continue

    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"❌ 読み込み失敗: {input_path} - {e}")
        continue

    master = pd.read_csv(master_path)
    df["prefecture"] = df["prefecture"].str.strip().str.replace("県|府|都", "", regex=True).str[:2]
    master["prefecture"] = master["prefecture"].str.strip().str.replace("県|府|都", "", regex=True).str[:2]
    df = df.merge(master[['prefecture', 'area', 'group']], on="prefecture", how="left")

    features = []
    for (d, v, r), g in df.groupby(["date", "venue_id", "race_no"]):
        race_dict = {
            "date": d,
            "venue_id": v,
            "race_no": r,
        }
        # num_lines（NaN除外）
        num_lines = g["line_id"].nunique(dropna=True)

        # num_solo（line_idがNaN）
        num_solo = g["line_id"].isna().sum()

        # avg_line_size（NaN除外）
        avg_line_size = g.dropna(subset=["line_id"]).groupby("line_id").size().mean()

        # leader_count（line_pos==1）
        leader_count = (g["line_pos"] == 1).sum()

        # group_diversity（出走選手の地区数）
        group_diversity = g["group"].nunique()

        # has_cross_area_line（1つのline_id内に複数groupが存在）
        cross_area = (
            g.dropna(subset=["line_id"])
             .groupby("line_id")["group"]
             .nunique()
             .gt(1)
             .any()
        )

        race_dict.update({
            "num_lines": num_lines,
            "num_solo": num_solo,
            "avg_line_size": avg_line_size,
            "leader_count": leader_count,
            "group_diversity": group_diversity,
            "has_cross_area_line": cross_area
        })
        features.append(race_dict)

    all_features.extend(features)

# 最終出力
out_df = pd.DataFrame(all_features)
output_path = Path(f"data/3rd/tmp/step0_race_features.csv")
out_df.to_csv(output_path, index=False)
print(f"🎉 出力完了: {output_path}")