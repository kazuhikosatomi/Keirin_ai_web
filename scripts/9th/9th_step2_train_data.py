import pandas as pd
from pathlib import Path
from argparse import ArgumentParser
from datetime import datetime, timedelta

parser = ArgumentParser()
parser.add_argument("--date", required=True, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()
date = args.date
RESULTS_DIR = Path("data/results")
RACER_STATS_PATH = Path("data/9th/tmp/step1_racer_stats.csv")
OUTPUT_PATH = Path("data/9th/tmp/step2_train_data.csv")

# ---- Logging: Start ----
SCRIPT_NAME = "9th_step2_train_data.py"
target_date_dt = datetime.strptime(date, "%Y-%m-%d")
window_start = (target_date_dt - timedelta(days=3*365)).date()
window_end = (target_date_dt - timedelta(days=1)).date()
print(f"🚀 [START] {SCRIPT_NAME} target_date={target_date_dt.date()} window=({window_start} ~ {window_end})")
# ---- /Logging: Start ----

# 2015〜基準年のresults CSVを読み込み
end_year = datetime.strptime(date, "%Y-%m-%d").year
start_year = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=3*365)).year
dfs = []
for year in range(start_year, end_year + 1):
    for file in sorted((RESULTS_DIR / str(year)).glob("results_*.csv")):
        df = pd.read_csv(file)
        dfs.append(df)

# 結合・整形
df_all = pd.concat(dfs, ignore_index=True)
print(f"📊 結合済み: {len(df_all)} 件")

# 必要な列だけ抽出
columns = [
    "racer_id", "date", "car_no", "rank", "line_pos", "line_id",
    "grade", "venue_id", "prefecture", "race_no", "age"
]
df_all = df_all[columns]
df_all["date"] = pd.to_datetime(df_all["date"])
df_all = df_all[df_all["date"] < pd.to_datetime(date)]
df_all = df_all[df_all["date"] >= pd.to_datetime(date) - pd.Timedelta(days=3*365)]

# 戦法・勝率などの集計データと結合
# Read racer_stats and remove duplicate 'prefecture' column if present
racer_stats = pd.read_csv(RACER_STATS_PATH)
racer_stats = racer_stats.drop(columns=["prefecture"], errors="ignore")
# G1〜F2に分けたrateのみ使用し、単純なrate列（win_rate, top2_rate, top3_rate）は除外
rate_cols_to_exclude = ["win_rate", "top2_rate", "top3_rate"]
rate_cols = [col for col in racer_stats.columns if col not in rate_cols_to_exclude]
df_merged = pd.merge(df_all, racer_stats[rate_cols], on="racer_id", how="left")

train_data_list = [df_merged]

train_df = pd.concat(train_data_list, ignore_index=True)

# ラベルデータの読み込みと結合（デバッグ付き）
labels_path = Path("data/arare/arare0_arare_labels.csv")
if labels_path.exists():
    labels_df = pd.read_csv(labels_path)
    labels_df["date"] = pd.to_datetime(labels_df["date"])
    train_df["date"] = pd.to_datetime(train_df["date"])

    # Match only on the exact date (day level), remove time component
    labels_df["date"] = labels_df["date"].dt.normalize()
    train_df["date"] = train_df["date"].dt.normalize()

    for col in ["venue_id", "race_no"]:
        labels_df[col] = labels_df[col].astype(int)
        train_df[col] = train_df[col].astype(int)


    train_df = pd.merge(
        train_df,
        labels_df[["date", "venue_id", "race_no", "is_arare"]],
        on=["date", "venue_id", "race_no"],
        how="left"
    )
    print(f"🔗 ラベル結合: {labels_df.shape[0]} 件")
    print(f"🧪 is_arare null件数: {train_df['is_arare'].isna().sum()}")
else:
    print(f"⚠️ ラベルファイルが見つかりません: {labels_path}")

# 前日の日付を取得
current_date = datetime.strptime(date, "%Y-%m-%d")
prev_date = (current_date - timedelta(days=1)).strftime("%Y-%m-%d")

# 前日のフィードバックファイルを結合（荒れ度フィードバック）
feedback_path = Path(f"data/9th/step7/step7_train_feedback_arare_{prev_date}.csv")
if feedback_path.exists():
    print(f"🔁 前日フィードバック読み込み: {feedback_path}")
    feedback_df = pd.read_csv(feedback_path)

    # --- 正規化: 型とキーを揃える ---
    # train_df 側を日付正規化 & ID を Int64 に
    train_df["date"] = pd.to_datetime(train_df["date"]).dt.normalize()
    for c in ["venue_id", "race_no"]:
        if c in train_df.columns:
            train_df[c] = train_df[c].astype("Int64")

    # feedback 側: 存在する列だけ使う
    available_cols = [c for c in ["date", "venue_id", "race_no", "racer_id", "hit"] if c in feedback_df.columns]
    feedback_df = feedback_df[available_cols].copy()

    if "date" in feedback_df.columns:
        feedback_df["date"] = pd.to_datetime(feedback_df["date"]).dt.normalize()
    for c in ["venue_id", "race_no", "racer_id"]:
        if c in feedback_df.columns:
            # 数値化できない値が混入しても落ちないように
            feedback_df[c] = pd.to_numeric(feedback_df[c], errors="coerce").astype("Int64")

    # hit が無ければ作る（下流安定化）
    if "hit" not in feedback_df.columns:
        feedback_df["hit"] = 0

    # 重複除去
    feedback_df = feedback_df.drop_duplicates()

    # --- マージ戦略 ---
    if "racer_id" in feedback_df.columns:
        # ✅ 選手単位で精密に結合
        before_cols = set(train_df.columns)
        train_df = train_df.merge(
            feedback_df[["date", "venue_id", "race_no", "racer_id", "hit"]],
            on=["date", "venue_id", "race_no", "racer_id"],
            how="left"
        )
        print("🔗 フィードバック結合: 選手単位 (date, venue_id, race_no, racer_id)")
    else:
        # ✅ レース単位でブロードキャスト結合（同一レースの全選手に hit を配布）
        before_cols = set(train_df.columns)
        train_df = train_df.merge(
            feedback_df[["date", "venue_id", "race_no", "hit"]],
            on=["date", "venue_id", "race_no"],
            how="left"
        )
        print("🔗 フィードバック結合: レース単位 (date, venue_id, race_no) → 全選手へブロードキャスト")

    # 追加された列の確認ログ
    added_cols = sorted(list(set(train_df.columns) - before_cols))
    if added_cols:
        print(f"🧩 追加カラム: {added_cols}")
else:
    print(f"⚠️ フィードバックファイルなし: {feedback_path}")

# 出力
train_df.to_csv(OUTPUT_PATH, index=False)
print(f"📤 上書き保存: {OUTPUT_PATH}")
# ---- Logging: End ----
print(f"✅ [END] {SCRIPT_NAME} output={OUTPUT_PATH} rows={len(train_df)}")
# ---- /Logging: End ----