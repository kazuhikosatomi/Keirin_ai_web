import pandas as pd
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()

base_date = pd.to_datetime(args.date) - pd.Timedelta(days=1)
start_date = base_date - pd.DateOffset(years=3)
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
            "avg_line_size": g.groupby("line_id").size().mean(),
            "std_line_size": g.groupby("line_id").size().std(ddof=0),
            "num_solo": (g.groupby("line_id").size() == 1).sum(),
            "num_lines": g["line_id"].nunique(),
            "leader_count": (g["line_pos"] == 1).sum(),
            "group_diversity": g["group"].nunique(),
            "has_cross_area_line": int(g.groupby("line_id")["area"].nunique().gt(1).any())
        }
        features.append(race_dict)

    all_features.extend(features)
    print(f"✅ 処理完了: {date}")

# 最終出力
out_df = pd.DataFrame(all_features)
output_path = Path(f"data/6th/tmp/step0_race_features_{start_date.date()}_to_{base_date.date()}.csv")
out_df.to_csv(output_path, index=False)
print(f"🎉 出力完了: {output_path}")