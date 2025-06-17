import pandas as pd
from tqdm import tqdm
import os

# 🔧 対象日付（予測対象）
TARGET_DATE = "2025-01-01"

# 🔍 エントリーファイル（あれば使用、なければresultsから作成）
ENTRY_PATH = f"data/entries/2025/entry_{TARGET_DATE}.csv"
RESULTS_PATH = f"data/results/2025/results_{TARGET_DATE}.csv"
OUTPUT_PATH = f"data/5th/stepD_predict_entry_like_{TARGET_DATE}.csv"

if os.path.exists(ENTRY_PATH):
    print(f"📋 entryファイルを読み込み: {ENTRY_PATH}")
    df = pd.read_csv(ENTRY_PATH)
else:
    print(f"📋 entryファイルが見つからないため、resultsから生成します: {RESULTS_PATH}")
    if not os.path.exists(RESULTS_PATH):
        raise FileNotFoundError(f"❌ {RESULTS_PATH} が存在しません")
    df = pd.read_csv(RESULTS_PATH)

    # 加工処理（4th_step4と同等）
    df["style_escape"] = (df["finish_tactics"] == "逃").astype(int)
    df["style_sprint"] = (df["finish_tactics"] == "捲").astype(int)
    df["style_chase"] = (df["finish_tactics"] == "差").astype(int)
    df["style_other"] = (df["finish_tactics"] == "マ").astype(int)
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

    df = df[[
        "date", "venue_id", "race_no", "car_no", "racer_id", "age", "grade",
        "rank", "line_id", "line_pos", "style_escape", "style_sprint", "style_chase", "style_other"
    ]]

# 💾 出力
df.to_csv(OUTPUT_PATH, index=False)
print(f"✅ 出力完了: {len(df)} 件 → {OUTPUT_PATH}")