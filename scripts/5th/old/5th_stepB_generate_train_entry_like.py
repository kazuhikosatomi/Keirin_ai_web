import pandas as pd
from pathlib import Path
from tqdm import tqdm

# 入力パス
LABEL_FILE = Path("data/5th/stepA_arare_labels_2022_to_2024.csv")
RESULTS_DIR = Path("data/results/")
OUTPUT_FILE = Path("data/5th/stepB_train_entry_like.csv")

# ラベル読み込み
labels = pd.read_csv(LABEL_FILE)
labels["date"] = pd.to_datetime(labels["date"])
labels["date_str"] = labels["date"].dt.strftime("%Y-%m-%d")

records = []

# 各レースファイルの読み込み後に style_ フラグを追加する関数
def add_finish_tactics_flags(df):
    df["style_escape"] = (df["finish_tactics"] == "逃").astype(int)
    df["style_sprint"] = (df["finish_tactics"] == "捲").astype(int)
    df["style_chase"] = (df["finish_tactics"] == "差").astype(int)
    df["style_other"] = (df["finish_tactics"] == "マ").astype(int)
    return df

for _, row in tqdm(labels.iterrows(), total=len(labels)):
    date = row["date_str"]
    venue_id = row["venue_id"]
    race_no = row["race_no"]
    label = row["label"]

    results_file = RESULTS_DIR / f"{row['date'].year}" / f"results_{date}.csv"
    if not results_file.exists():
        print(f"⚠️ {results_file} が存在しません")
        continue

    df = pd.read_csv(results_file)
    race_df = df[
        (df["venue_id"] == venue_id) &
        (df["race_no"] == race_no)
    ].copy()
    race_df = add_finish_tactics_flags(race_df)

    if race_df.empty:
        print(f"⚠️ 該当データなし: {date}, venue_id={venue_id}, race_no={race_no}")
        continue

    # 特徴量選択
    race_df["date"] = date
    race_df["label"] = label
    race_df = race_df[[
        "date", "venue_id", "race_no", "car_no", "racer_id", "age", "grade",
        "rank", "line_id", "line_pos", "style_escape", "style_sprint", "style_chase", "style_other", "label"
    ]]

    records.append(race_df)

# 結合と保存
if records:
    out_df = pd.concat(records, ignore_index=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ 出力完了: {len(out_df)} 件 → {OUTPUT_FILE}")
else:
    print("❌ 有効なデータがありませんでした")