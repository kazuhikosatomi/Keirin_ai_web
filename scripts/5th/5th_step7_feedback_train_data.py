import pandas as pd
import argparse
from datetime import datetime
from pathlib import Path

STEP6_DIR = Path("data/5th/step6")
ENTRY_DIR = Path("data/5th/tmp")
OUTPUT_DIR = Path("data/5th/step7")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日付 (YYYY-MM-DD)")
    return parser.parse_args()

def main():
    args = parse_args()
    target_date = args.date

    # ファイルパス
    step6_path = STEP6_DIR / f"step6_evaluation_arare_{target_date}.csv"
    entry_path = ENTRY_DIR / f"step5_arare_predictions.csv"
    output_path = OUTPUT_DIR / f"step7_train_feedback_arare_{target_date}.csv"

    # ファイル読み込み
    if not step6_path.exists() or not entry_path.exists():
        print("⚠️ 評価ファイルまたはエントリーファイルが見つかりません")
        return

    print(f"📥 評価ファイル読み込み: {step6_path}")
    print(f"📥 エントリーファイル読み込み: {entry_path}")
    eval_df = pd.read_csv(step6_path)
    entry_df = pd.read_csv(entry_path)

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
    entry_df = merged_df

    # 欠損は0に
    entry_df["is_arare"] = entry_df["is_arare"].fillna(0).astype(int)
    entry_df["hit"] = entry_df["is_arare"]

    # 出力先作成と保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entry_df.to_csv(output_path, index=False)
    print(f"✅ フィードバック学習データを保存しました: {output_path}")

if __name__ == "__main__":
    main()