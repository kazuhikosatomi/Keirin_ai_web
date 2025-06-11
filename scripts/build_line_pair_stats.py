import os
import pandas as pd
from glob import glob
from itertools import combinations
from collections import defaultdict

# === 設定 ===
RESULTS_DIR = "data/results/"
OUTPUT_CSV = "data/line_stats/line_pair_stats.csv"
os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

# === ペア出現回数をカウントする辞書 ===
pair_counter = defaultdict(set)

# === 過去のresultsデータをすべて探索 ===
result_files = sorted(glob(os.path.join(RESULTS_DIR, "*/results_*.csv")))

print(f"📁 処理対象ファイル数: {len(result_files)}")

for file_path in result_files:
    try:
        df = pd.read_csv(file_path, dtype={"racer_id": str, "line_id": str})
        required_columns = {"date", "race_no", "racer_id", "line_id"}
        if not required_columns.issubset(df.columns):
            print(f"⚠️ スキップ（必要なカラムなし）: {file_path}")
            print(f"🔍 実際のカラム: {df.columns.tolist()}")
            continue

        # Drop rows with missing required fields
        df = df.dropna(subset=["date", "race_no", "racer_id", "line_id"])

        for (date, race_no), race_group in df.groupby(["date", "race_no"]):
            for line_id, line_group in race_group.groupby("line_id"):
                racers = sorted(line_group["racer_id"].unique())
                for pair in combinations(racers, 2):
                    # ソートして順序を統一
                    pair_key = tuple(sorted(pair))
                    pair_counter[pair_key].add((date, race_no))
    except Exception as e:
        print(f"❌ 読み込み失敗: {file_path} ({e})")

# === DataFrameに変換 ===
data = [(r1, r2, len(occurrences)) for (r1, r2), occurrences in pair_counter.items()]
pair_df = pd.DataFrame(data, columns=["racer_id_1", "racer_id_2", "count"])
pair_df = pair_df.sort_values("count", ascending=False)
pair_df.to_csv(OUTPUT_CSV, index=False)
print(f"✅ 出力完了: {OUTPUT_CSV} ({len(pair_df)} 件)")