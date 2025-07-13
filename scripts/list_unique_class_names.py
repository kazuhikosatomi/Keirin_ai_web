import os
import pandas as pd
from collections import Counter

BASE_DIR = "data/race_grade"
OUTPUT_FILE = "class_name_summary.csv"

class_names = []

# 年フォルダを探索
for year in os.listdir(BASE_DIR):
    year_path = os.path.join(BASE_DIR, year)
    if not os.path.isdir(year_path):
        continue

    # ファイルを探索
    for fname in os.listdir(year_path):
        if not fname.endswith(".csv"):
            continue

        fpath = os.path.join(year_path, fname)
        try:
            df = pd.read_csv(fpath)
            if "class_name" in df.columns:
                class_names.extend(df["class_name"].dropna().astype(str).tolist())
        except Exception as e:
            print(f"⚠️ 読み込みエラー: {fpath} ({e})")

# 集計してDataFrame化
counter = Counter(class_names)
summary_df = pd.DataFrame(counter.items(), columns=["class_name", "count"])
summary_df = summary_df.sort_values(by="count", ascending=False)

# CSV出力
summary_df.to_csv(OUTPUT_FILE, index=False)

print(f"✅ 出力完了: {OUTPUT_FILE}")
