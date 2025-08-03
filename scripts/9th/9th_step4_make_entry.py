import pandas as pd
import argparse
from pathlib import Path

def main(target_date: str):
    base_dir = Path("data/9th/tmp")
    if (Path(f"data/entries/{target_date[:4]}/entry_{target_date}.csv")).exists():
        entry_path = Path(f"data/entries/{target_date[:4]}/entry_{target_date}.csv")
    else:
        entry_path = Path(f"data/results/{target_date[:4]}/results_{target_date}.csv")
    train_path = base_dir / "step2_train_data.csv"
    output_path = Path("data/9th/tmp") / "step4_make_entry.csv"

    entry_df = pd.read_csv(entry_path)
    # 不要なrank列を削除（出走表に含まれるのは不自然）
    if "rank" in entry_df.columns:
        entry_df = entry_df.drop(columns=["rank"])
    train_df = pd.read_csv(train_path)

    # entry_df に含まれるカラムと重複するものは除外（racer_id, date を除く）
    drop_cols = [col for col in train_df.columns if col in entry_df.columns and col not in ["racer_id", "date"]]
    train_df = train_df.drop(columns=drop_cols)

    # ✅ 'hit'列が含まれていれば除外（予測には不要）
    if "hit" in train_df.columns:
        train_df = train_df.drop(columns=["hit"])

    # 最新日のレコードだけを抽出（選手ごとに1件だけ）
    train_df_latest = train_df.sort_values("date").drop_duplicates(subset=["racer_id"], keep="last")

    # 結合（racer_idのみ）
    merged = pd.merge(entry_df, train_df_latest, on="racer_id", how="left")
    if "date_y" in merged.columns:
        merged = merged.drop(columns=["date_y"])
        merged = merged.rename(columns={"date_x": "date"})

    # 念のため再度rank列を削除
    if "rank" in merged.columns:
        merged = merged.drop(columns=["rank"])

    # 出力保存
    merged.to_csv(output_path, index=False)
    print(f"📤 上書き保存: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付 (例: 2020-01-03)")
    args = parser.parse_args()

    main(args.date)