import os
import pandas as pd
from glob import glob
from tqdm import tqdm
from pathlib import Path

ARARE_THRESHOLD = 300.0  # 三連単 300倍以上を"荒れ"と定義
BET_CODE_SANRENTAN = 5

def extract_labels(results_dir, odds_dir, output_path):
    records = []
    result_files = sorted(glob(os.path.join(results_dir, "results_2023-*.csv")))

    for result_file in tqdm(result_files):
        date_str = Path(result_file).stem[-10:]
        odds_file = os.path.join(odds_dir, f"odds_{date_str}.csv")
        if not os.path.exists(odds_file):
            continue

        try:
            df_results = pd.read_csv(result_file)
            df_odds = pd.read_csv(odds_file)
        except Exception as e:
            print(f"❌ 読み込みエラー: {date_str} -> {e}")
            continue

        for (venue_id, race_no), group_df in df_results.groupby(["venue_id", "race_no"]):
            rank_df = group_df.sort_values("rank")
            if rank_df["rank"].nunique() < 3:
                continue

            top3 = rank_df.head(3).sort_values("rank")
            car_1, car_2, car_3 = top3["car_no"].tolist()

            odds_row = df_odds[
                (df_odds["venue_id"] == venue_id) &
                (df_odds["race_no"] == race_no) &
                (df_odds["bet_code"] == BET_CODE_SANRENTAN) &
                (df_odds["car_no1"] == car_1) &
                (df_odds["car_no2"] == car_2) &
                (df_odds["car_no3"] == car_3)
            ]

            if odds_row.empty:
                continue

            odds = odds_row["odds_1"].values[0]
            is_arare = int(odds >= ARARE_THRESHOLD)

            records.append({
                "date": date_str,
                "venue_id": venue_id,
                "race_no": race_no,
                "car_1": car_1,
                "car_2": car_2,
                "car_3": car_3,
                "odds": odds,
                "is_arare": is_arare
            })

    df_out = pd.DataFrame(records)
    df_out = df_out[["date", "venue_id", "race_no", "car_1", "car_2", "car_3", "odds", "is_arare"]]
    df_out.to_csv(output_path, index=False)
    print(f"✅ 保存完了: {output_path}")

if __name__ == "__main__":
    results_dir = "data/results/2023"
    odds_dir = "data/odds/2023"
    output_path = "data/7th/labels_arare_2023.csv"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    extract_labels(results_dir, odds_dir, output_path)
