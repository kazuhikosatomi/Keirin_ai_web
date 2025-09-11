import pandas as pd
import argparse
from datetime import datetime
from pathlib import Path

STEP6_DIR = Path("data/9th/step6")
ENTRY_DIR = Path("data/9th/step5c")
OUTPUT_DIR = Path("data/9th/step7")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日付 (YYYY-MM-DD)")
    return parser.parse_args()

def main():
    args = parse_args()
    target_date = args.date

    print(f"\n🚀 [START] 9th_step7_feedback_data.py target_date={target_date}")

    # ファイルパス
    step6_path = STEP6_DIR / f"step6_evaluation_arare_{target_date}.csv"
    entry_path = ENTRY_DIR / f"step5c_predictions_ranked_{target_date}.csv"
    output_path = OUTPUT_DIR / f"step7_train_feedback_arare_{target_date}.csv"

    # ファイル読み込み
    missing = []
    if not step6_path.exists():
        missing.append(str(step6_path))
    if not entry_path.exists():
        missing.append(str(entry_path))
    if missing:
        print("⚠️ 入力ファイルが見つかりません:\n  " + "\n  ".join(missing))
        print("🏁 [END] 9th_step7_feedback_data.py (no output)")
        return

    eval_df = pd.read_csv(step6_path)
    entry_df = pd.read_csv(entry_path)
    print(f"📥 評価ファイル読み込み: {step6_path} rows={len(eval_df)}")
    print(f"📥 予測ランキング読み込み: {entry_path} rows={len(entry_df)}")

    entry_df["date"] = entry_df["date"].astype(str)
    eval_df["date"] = eval_df["date"].astype(str)

    # 型を明示的に揃える
    eval_df["venue_id"] = eval_df["venue_id"].astype(int)
    eval_df["race_no"] = eval_df["race_no"].astype(int)
    entry_df["venue_id"] = entry_df["venue_id"].astype(int)
    entry_df["race_no"] = entry_df["race_no"].astype(int)

    before_merge = entry_df.shape[0]
    merged_df = pd.merge(entry_df, eval_df[["date", "venue_id", "race_no", "is_arare"]],
                         on=["date", "venue_id", "race_no"], how="left")
    after_merge = merged_df["is_arare"].notna().sum()
    print(f"📊 マージ完了: entry_rows={before_merge} / is_arare付与={after_merge}")
    entry_df = merged_df

    # 欠損は0に
    entry_df["is_arare"] = entry_df["is_arare"].fillna(0).astype(int)
    entry_df["hit"] = entry_df["is_arare"]

    # 出力先作成と保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entry_df.to_csv(output_path, index=False)
    print(f"💾 保存完了: {output_path}")
    print("✅ [END] 9th_step7_feedback_data.py")

if __name__ == "__main__":
    main()