import pandas as pd
import argparse
from datetime import datetime, timedelta
from pathlib import Path

RESULTS_DIR = Path("data/results")
EVAL_DIR = Path("data/5th/step6")
OUTPUT_PATH = Path("data/5th/step7")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日付 (YYYY-MM-DD)")
    return parser.parse_args()

def main():
    args = parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    eval_path = f"{EVAL_DIR}/step6_evaluation_arare_{target_date}.csv"

    entry_path = f"data/5th/tmp/step4_entry_with_features.csv"
    entry_df = pd.read_csv(entry_path)
    # ⛑️ 強制的に date カラムを統一
    if "date_x" in entry_df.columns:
        entry_df = entry_df.rename(columns={"date_x": "date"})
    elif "date_y" in entry_df.columns and "date" not in entry_df.columns:
        entry_df = entry_df.rename(columns={"date_y": "date"})

    eval_df = pd.read_csv(eval_path)

    print("🔍 entry_df のカラム:", entry_df.columns.tolist())
    print("🔍 eval_df のカラム:", eval_df.columns.tolist())
    print("🔍 entry_df の先頭:\n", entry_df[["date", "venue_id", "race_no"]].head())
    print("🔍 eval_df の先頭:\n", eval_df[["date", "venue_id", "race_no", "is_arare"]].head())

    entry_df["date"] = pd.to_datetime(entry_df["date"])
    # 🔄 Shift date back by one day to align with previous evaluation
    entry_df["date"] = entry_df["date"] - timedelta(days=1)
    entry_df["date"] = entry_df["date"].dt.strftime("%Y-%m-%d")
    eval_df["date"] = eval_df["date"].astype(str)

    eval_df = eval_df[["date", "venue_id", "race_no", "is_arare"]]

    print("🔍 マージキーの一致確認用")
    print("entry_dfのユニークなキー例:", entry_df[["date", "venue_id", "race_no"]].drop_duplicates().head())
    print("eval_dfのユニークなキー例:", eval_df[["date", "venue_id", "race_no"]].drop_duplicates().head())

    merged = pd.merge(entry_df, eval_df, on=["date", "venue_id", "race_no"], how="inner")

    print("🔁 マージ後のカラム一覧:", merged.columns.tolist())

    if "is_arare" not in merged.columns:
        raise KeyError("❌ 'is_arare' カラムが結合後に見つかりません。date/venue_id/race_no の型や値を確認してください。")

    merged["hit"] = merged["is_arare"]  # 荒れたレースならすべての選手に 1 を付与

    feature_cols = [
        "racer_id", "date", "car_no", "rank", "line_pos", "line_id",
        "grade", "venue_id", "prefecture", "race_no", "age", "hit"
    ]

    output_path = OUTPUT_PATH / f"step7_train_feedback_arare_{target_date}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged[feature_cols].to_csv(output_path, index=False)
    print(f"✅ フィードバック学習データを保存しました: {output_path}")

if __name__ == "__main__":
    main()