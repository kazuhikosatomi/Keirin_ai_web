import pandas as pd
from tqdm import tqdm
import os
from glob import glob

# パス
entry_dir = "data/entries/2023/"
entry_paths = sorted(glob(os.path.join(entry_dir, "entry_2023-*.csv")))
venue_master_path = "data/master/venue_master.csv"
output_path = "data/7th/step1_race_features.csv"

entry_list = []
for path in entry_paths:
    try:
        df = pd.read_csv(path)
        df["source_path"] = path  # デバッグ用（任意）
        entry_list.append(df)
    except Exception as e:
        print(f"⚠️ 読み込み失敗: {path} ({e})")

entry_df = pd.concat(entry_list, ignore_index=True)

venue_master = pd.read_csv(venue_master_path)

prefecture_master = pd.read_csv("data/master/prefectures_master.csv")

# 都道府県名の2文字変換列を追加
prefecture_master["pref_2char"] = prefecture_master["prefecture"].str[:2]

# entry_df 側も2文字列を用意
entry_df["pref_2char"] = entry_df["prefecture"].astype(str).str[:2]

# マージ
entry_df = entry_df.merge(prefecture_master[["pref_2char", "area"]], on="pref_2char", how="left")

entry_df.drop(columns=["pref_2char"], inplace=True)

venue_dict = venue_master.set_index("venue_id")[["track_length_m", "virtual_straight_m", "roof_type"]].to_dict(orient="index")

# 出力用
records = []

# レース単位で集計（date, venue_id, race_no をキーに）
for (date, venue_id, race_no), g in tqdm(entry_df.groupby(["date", "venue_id", "race_no"])):
    venue_info = venue_dict.get(venue_id, {})
    venue_length = venue_info.get("track_length_m")
    straight_length = venue_info.get("virtual_straight_m")

    line_sizes = g.groupby("line_id").size()

    max_line_size = line_sizes.max()
    age_std = g["age"].std(ddof=0)
    score_std = g["score"].std(ddof=0)
    score_max = g["score"].max()
    score_min = g["score"].min()
    escape_max = g["style_escape"].max()
    sprint_max = g["style_sprint"].max()
    roof_type = venue_info.get("roof_type")

    record = {
        "date": date,
        "venue_id": venue_id,
        "race_no": race_no,
        "num_racers": len(g),
        "avg_age": g["age"].mean(),
        "num_lines": g["line_id"].nunique(),
        "line_size_std": line_sizes.std(ddof=0),
        "num_solo": (line_sizes == 1).sum(),
        "venue_length": venue_length,
        "straight_length": straight_length,
        "has_cross_area_line": int(g.groupby("line_id")["area"].nunique().gt(1).any()),
        "max_line_size": max_line_size,
        "age_std": age_std,
        "score_std": score_std,
        "score_max": score_max,
        "score_min": score_min,
        "escape_max": escape_max,
        "sprint_max": sprint_max,
        "roof_type": roof_type,
    }
    records.append(record)

# 出力
df_out = pd.DataFrame(records)
df_out.to_csv(output_path, index=False)
print(f"✅ 出力完了: {output_path}")