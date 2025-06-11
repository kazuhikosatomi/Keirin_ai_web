import os
import argparse
import pandas as pd
from tqdm import tqdm
from glob import glob

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--results_dir', type=str, default='data/results', help='Path to results folder')
    parser.add_argument('--output', type=str, default='data/train/train_racer_level.csv', help='Output file path')
    return parser.parse_args()

def load_results_in_range(start_date, end_date, results_dir):
    all_files = sorted(glob(os.path.join(results_dir, '*', 'results_*.csv')))
    dfs = []
    for f in tqdm(all_files, desc="読み込み中"):
        date = os.path.basename(f).replace("results_", "").replace(".csv", "")
        if start_date <= date <= end_date:
            df = pd.read_csv(f)
            df['date'] = date
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def process_racer_stats(df_results):
    df_results = df_results.dropna(subset=["racer_id"])
    df_results["rank"] = df_results["rank"].astype(str)

    def win_flag(rank):
        return 1 if rank == "1" else 0

    def top3_flag(rank):
        return 1 if rank in ["1", "2", "3"] else 0

    df_results["win"] = df_results["rank"].apply(win_flag)
    df_results["top3"] = df_results["rank"].apply(top3_flag)

    df_grouped = df_results.groupby("racer_id").agg(
        races=("rank", "count"),
        win_cnt=("win", "sum"),
        top3_cnt=("top3", "sum")
    ).reset_index()

    df_grouped["win_rate"] = df_grouped["win_cnt"] / df_grouped["races"]
    df_grouped["top3_rate"] = df_grouped["top3_cnt"] / df_grouped["races"]

    return df_grouped[["racer_id", "races", "win_rate", "top3_rate"]]

def main():
    args = parse_args()
    df_results = load_results_in_range(args.start, args.end, args.results_dir)
    df_stats = process_racer_stats(df_results)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df_stats.to_csv(args.output, index=False)
    print(f"✅ 出力完了: {args.output}（件数: {len(df_stats)}）")

if __name__ == '__main__':
    main()