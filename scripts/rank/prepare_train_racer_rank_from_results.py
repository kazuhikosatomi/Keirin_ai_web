import pandas as pd
import os
from tqdm import tqdm
import argparse

def is_valid_result(row):
    try:
        int(row["rank"])
        return True
    except:
        return False

def create_entry_like_features(df_result):
    df = df_result.copy()
    df = df[df["rank"].notna()]
    df["rank"] = df["rank"].astype(str)
    df = df[df["rank"].str.match(r"^\d$")]
    df["rank"] = df["rank"].astype(int)

    df["car_no"] = df["car_no"] if "car_no" in df.columns else df["car_number"]
    if "race_id" in df.columns:
        df = df[["race_id", "racer_id", "car_no", "rank"]]
    else:
        df["race_id"] = None
        df = df[["race_id", "racer_id", "car_no", "rank"]]
    return df

def prepare_dataset(year, results_dir="data/results", output_path=None):
    result_files = sorted([
        f for f in os.listdir(f"{results_dir}/{year}")
        if f.startswith("results_") and f.endswith(".csv")
    ])

    all_data = []
    for file in tqdm(result_files, desc=f"Processing {year}"):
        df_result = pd.read_csv(f"{results_dir}/{year}/{file}")
        df_feat = create_entry_like_features(df_result)
        all_data.append(df_feat)

    df_all = pd.concat(all_data, ignore_index=True)
    if output_path is None:
        output_path = f"data/train/train_racer_rank_{year}.csv"
    df_all.to_csv(output_path, index=False)
    print(f"✅ 保存完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True, help="対象の年 (例: 2020)")
    args = parser.parse_args()

    prepare_dataset(args.year)