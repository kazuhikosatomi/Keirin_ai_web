import os
import argparse
import pandas as pd
from glob import glob

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", type=str, required=True, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, required=True, help="終了日 (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="data/train/train_racer_level.csv")
    return parser.parse_args()

def load_results_in_range(start_date, end_date):
    result_files = sorted(glob("data/results/2025/results_2025-*.csv"))
    all_dfs = []
    for file in result_files:
        date_str = os.path.basename(file).split("_")[1].split(".")[0]
        if start_date <= date_str <= end_date:
            df = pd.read_csv(file)
            df["date"] = date_str
            all_dfs.append(df)
    if not all_dfs:
        print("❌ 指定範囲に該当するデータが存在しません")
        return pd.DataFrame()
    return pd.concat(all_dfs, ignore_index=True)

def extract_features(df):
    # racer_idや基本的な集計例（簡易版）
    features = df.groupby(["racer_id", "date"]).agg({
        "car_no": "first",
        "age": "first",
        "rank": lambda x: pd.to_numeric(x, errors="coerce").mean(),
        "line_pos": "first",
        "line_id": "first",
        "grade": "first",
        "venue_id": "first",
        "prefecture": "first",
        "race_no": "first"
    }).reset_index()

    # スタイルの例（仮に one-hot 風に整備）
    for style in ["style_escape", "style_sprint", "style_chase", "style_other"]:
        if style in df.columns:
            features[style] = df.groupby(["racer_id", "date"])[style].mean().values
        else:
            features[style] = 0.0

    features["win_rate"] = 1.0 / features["rank"]
    # Ensure "date" column is datetime64[ns] dtype
    features["date"] = features["date"].astype(str).str.strip().str.replace("　", "").str.replace("\u200b", "")
    features["date"] = pd.to_datetime(features["date"], format="%Y-%m-%d", errors="coerce")
    return features

def main():
    args = parse_args()
    df_all = load_results_in_range(args.start_date, args.end_date)
    if df_all.empty:
        return
    df_features = extract_features(df_all)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    # Save as string format for date
    df_features["date"] = df_features["date"].dt.strftime("%Y-%m-%d")
    df_features.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"✅ {args.output} に出力しました")

if __name__ == "__main__":
    main()