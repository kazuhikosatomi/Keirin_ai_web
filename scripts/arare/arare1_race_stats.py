import pandas as pd
import argparse
from pathlib import Path
from datetime import datetime, date, timedelta

import unicodedata

Path("data/arare").mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()

# Add date range for SQL query
target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
start_date = date(2021, 1, 1)
end_date = target_date - timedelta(days=1)

date_list = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()

master_path = Path("data/master/prefectures_master.csv")
all_features = []

for date in date_list:
    input_path = Path(f"data/results/{date[:4]}/results_{date}.csv")
    if not input_path.exists():
        print(f"⏭️ スキップ: {input_path}（ファイルなし）")
        continue

    try:
        df = pd.read_csv(input_path)
        # line_id の空文字や 'nan' を NaN に変換
        df["line_id"] = df["line_id"].replace(["", "nan"], pd.NA)
    except Exception as e:
        print(f"❌ 読み込み失敗: {input_path} - {e}")
        continue

    entry_path = Path(f"data/entries/{date[:4]}/entry_{date}.csv")
    if entry_path.exists():
        entry_df = pd.read_csv(entry_path)
        # 日付型の不一致を防ぐため、date列をstr型に変換
        entry_df["date"] = entry_df["date"].astype(str)
        # grade を半角英数字に変換（全角 → 半角）
        entry_df["grade"] = entry_df["grade"].apply(
            lambda x: unicodedata.normalize("NFKC", str(x)) if pd.notna(x) else x
        )
    else:
        entry_df = None

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

        # ラインの人数をカウントし、構成員1人のライン（単騎）を抽出
        line_counts = g["line_id"].value_counts()
        solo_line_ids = line_counts[line_counts == 1].index

        # 単騎とみなせる選手の数（構成員が1人の line_id を持つ選手）
        num_solo = g[g["line_id"].isin(solo_line_ids)].shape[0]

        # avg_line_size（NaN除外）
        avg_line_size = g.dropna(subset=["line_id"]).groupby("line_id").size().mean()
        std_line_size = g.dropna(subset=["line_id"]).groupby("line_id").size().std()
        max_line_size = g.dropna(subset=["line_id"]).groupby("line_id").size().max()

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

        if entry_df is not None:
            entry_g = entry_df[
                (entry_df["date"] == d) &
                (entry_df["venue_id"] == v) &
                (entry_df["race_no"] == r)
            ]
            score_std = entry_g["score"].std(ddof=0)
            score_max = entry_g["score"].max()
            score_min = entry_g["score"].min()
            escape_max = entry_g["style_escape"].max()
            sprint_max = entry_g["style_sprint"].max()

            num_racers = len(entry_g)
            num_SS = (entry_g["grade"] == "SS").sum()
            num_S1 = (entry_g["grade"] == "S1").sum()
            num_S2 = (entry_g["grade"] == "S2").sum()
            num_A1 = (entry_g["grade"] == "A1").sum()
            num_A2 = (entry_g["grade"] == "A2").sum()
            num_A3 = (entry_g["grade"] == "A3").sum()
            num_L1 = (entry_g["grade"] == "L1").sum()
            age_std = entry_g["age"].std(ddof=0)
            avg_top3_rate = entry_g["top3_rate"].mean()
            std_top3_rate = entry_g["top3_rate"].std(ddof=0)
            avg_top2_rate = entry_g["top2_rate"].mean()
            std_top2_rate = entry_g["top2_rate"].std(ddof=0)
            avg_win_rate = entry_g["win_rate"].mean()
            std_win_rate = entry_g["win_rate"].std(ddof=0)
            race_grade = entry_g["race_grade"].iloc[0] if ("race_grade" in entry_g.columns and not entry_g.empty) else None
        else:
            score_std = score_max = score_min = escape_max = sprint_max = None
            num_racers = num_SS = num_S1 = num_S2 = age_std = avg_top3_rate = std_top3_rate = None
            avg_top2_rate = std_top2_rate = avg_win_rate = std_win_rate = race_grade = None

        race_dict.update({
            "num_lines": num_lines,
            "num_solo": num_solo,
            "avg_line_size": avg_line_size,
            "std_line_size": std_line_size,
            "max_line_size": max_line_size,
            "leader_count": leader_count,
            "group_diversity": group_diversity,
            "has_cross_area_line": cross_area
        })
        race_dict.update({
            "num_racers": num_racers,
            "num_SS": num_SS,
            "num_S1": num_S1,
            "num_S2": num_S2,
            "num_A1": num_A1,
            "num_A2": num_A2,
            "num_A3": num_A3,
            "num_L1": num_L1,
            "age_std": age_std,
            "avg_top3_rate": avg_top3_rate,
            "std_top3_rate": std_top3_rate,
            "avg_top2_rate": avg_top2_rate,
            "std_top2_rate": std_top2_rate,
            "avg_win_rate": avg_win_rate,
            "std_win_rate": std_win_rate,
            "race_grade": race_grade
        })
        race_dict.update({
            "score_std": score_std,
            "score_max": score_max,
            "score_min": score_min,
            "escape_max": escape_max,
            "sprint_max": sprint_max
        })
        features.append(race_dict)

    all_features.extend(features)

# 最終出力
out_df = pd.DataFrame(all_features)
output_path = Path(f"data/arare/arare1_race_stats.csv")
out_df.to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")