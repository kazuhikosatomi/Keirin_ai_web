# scripts/rank/rank_step1_entry.py - results を entry_like に変換し、train_racer_level を付加

import pandas as pd

import argparse
from pathlib import Path

def generate_entry_like(date_str: str, include_extra: bool = False):
    input_path = Path(f"data/results/{date_str[:4]}/results_{date_str}.csv")
    output_path = Path(f"data/entries_like/entry_like_{date_str}.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"❌ ファイルが存在しません: {input_path}")
        return

    df = pd.read_csv(input_path, dtype=str)

    base_cols = ["racer_id", "car_no", "race_no", "venue_id", "date"]
    extra_cols = ["line_id", "line_pos", "rank"]

    # 存在するカラムだけを対象に
    selected_cols = base_cols.copy()
    if include_extra:
        selected_cols += [col for col in extra_cols if col in df.columns]

    df_entry_like = df[selected_cols]

    # 欠損チェック
    if df_entry_like['racer_id'].isna().any():
        print(f"⚠️ 注意: racer_id に欠損があります（{df_entry_like['racer_id'].isna().sum()} 件）")
        print(df_entry_like[df_entry_like['racer_id'].isna()].head())

    # 勝率などを join（あれば）
    try:
        df_train_stats = pd.read_csv("data/train/train_racer_level.csv", dtype={"racer_id": str})
        df_train_stats["racer_id"] = df_train_stats["racer_id"].str.strip()
        df_entry_like["racer_id"] = df_entry_like["racer_id"].str.strip()

        df_entry_like = df_entry_like.merge(df_train_stats, on="racer_id", how="left")
    except Exception as e:
        print(f"⚠️ train_racer_level の読み込みに失敗: {e}")

    df_entry_like.to_csv(output_path, index=False)
    print(f"✅ 出力完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="例: 2023-01-15")
    parser.add_argument("--include-extra", action="store_true", help="line_id, line_pos, rank を含める場合に指定")
    args = parser.parse_args()

    generate_entry_like(args.date, args.include_extra)