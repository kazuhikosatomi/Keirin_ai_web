import pandas as pd
import argparse
from pathlib import Path

def main(target_date: str):
    base_dir = Path("data/2nd/tmp")
    if (Path(f"data/entries/{target_date[:4]}/entry_{target_date}.csv")).exists():
        entry_path = Path(f"data/entries/{target_date[:4]}/entry_{target_date}.csv")
    else:
        entry_path = Path(f"data/results/{target_date[:4]}/results_{target_date}.csv")
    train_path = base_dir / "step2_train_racer_level.csv"
    output_path = Path("data/2nd/tmp") / "step4_entry_with_features.csv"

    entry_df = pd.read_csv(entry_path)
    train_df = pd.read_csv(train_path, low_memory=False)
    train_df["date"] = pd.to_datetime(train_df["date"], format='mixed').dt.strftime("%Y-%m-%d")
    # train_df = train_df[train_df["date"] == target_date]
    train_df.sort_values("date", ascending=False, inplace=True)
    train_df = train_df.drop_duplicates(subset=["racer_id"], keep="first")

    # entry_df に含まれるカラムと重複するものは除外（racer_id を除く）
    drop_cols = [col for col in train_df.columns if col in entry_df.columns and col != "racer_id"]
    train_df = train_df.drop(columns=drop_cols)

    # ✅ 'hit'列が含まれていれば除外（予測には不要）
    if "hit" in train_df.columns:
        train_df = train_df.drop(columns=["hit"])

    # 特徴量をマージ（racer_id をキーにする）
    merged = pd.merge(entry_df, train_df, on="racer_id", how="left")
    if 'area' not in merged.columns or 'group' not in merged.columns:
        print("⚠️ Warning: 'area' or 'group' not found after merge.")

    # 出力保存
    merged.to_csv(output_path, index=False)
    print(f"📤 上書き保存: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付 (例: 2020-01-03)")
    args = parser.parse_args()

    main(args.date)