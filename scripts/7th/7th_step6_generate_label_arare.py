import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

def run_steps_for_date(date_str: str) -> pd.DataFrame:
    results_path = Path(f"data/results/{date_str[:4]}/results_{date_str}.csv")
    odds_path = Path(f"data/odds/{date_str[:4]}/odds_{date_str}.csv")

    if not results_path.exists() or not odds_path.exists():
        return pd.DataFrame()

    results_df = pd.read_csv(results_path)
    odds_df = pd.read_csv(odds_path)

    # 使用可能なodds列を探索
    possible_odds_cols = ["odds1", "odds_1", "odds"]
    available_odds_col = next((col for col in possible_odds_cols if col in odds_df.columns), None)
    if available_odds_col is None:
        print(f"⚠️ {date_str}: オッズ列が見つかりませんでした。スキップします。")
        return pd.DataFrame()

    labels = []
    for (venue_id, race_no), group in results_df.groupby(["venue_id", "race_no"]):
        top3 = group[pd.to_numeric(group["rank"], errors="coerce") <= 3]
        if len(top3) != 3:
            continue

        try:
            combo = tuple(top3.sort_values("rank")["car_no"].astype(int).tolist())
        except ValueError:
            continue

        odds_filtered = odds_df[
            (odds_df["venue_id"] == venue_id) &
            (odds_df["race_no"] == race_no)
        ].dropna(subset=["car_1", "car_2", "car_3", available_odds_col])

        try:
            odds_filtered = odds_filtered.copy()
            odds_filtered["car_1"] = odds_filtered["car_1"].astype(int)
            odds_filtered["car_2"] = odds_filtered["car_2"].astype(int)
            odds_filtered["car_3"] = odds_filtered["car_3"].astype(int)
        except ValueError:
            continue

        matched = odds_filtered[
            (odds_filtered["car_1"] == combo[0]) &
            (odds_filtered["car_2"] == combo[1]) &
            (odds_filtered["car_3"] == combo[2])
        ]

        if matched.empty:
            continue

        odds = matched[available_odds_col].values[0]
        label = int(odds >= 300)

        labels.append({
            "date": date_str,
            "venue_id": venue_id,
            "race_no": race_no,
            "car_1": combo[0],
            "car_2": combo[1],
            "car_3": combo[2],
            "odds": odds,
            "is_arare": label  # 'label' を 'is_arare' に変更
        })

    return pd.DataFrame(labels)


def main():
    df = run_steps_for_date(target_date)
    if not df.empty:
        output_path = Path(f"data/7th/step6/step6_label_{target_date}.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ 出力完了: {len(df)} 件 → {output_path}")
    else:
        print(f"⚠️ {target_date}: 有効なデータが見つかりませんでした。")


if __name__ == "__main__":
    main()