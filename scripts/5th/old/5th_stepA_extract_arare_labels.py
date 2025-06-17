# scripts/5th/5th_stepA_extract_arare_labels.py
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

def extract_label_for_date(date_str):
    results_path = Path(f"data/results/{date_str[:4]}/results_{date_str}.csv")
    odds_path = Path(f"data/odds/{date_str[:4]}/odds_{date_str}.csv")

    if not results_path.exists() or not odds_path.exists():
        print(f"⚠️ {date_str} のファイルが見つかりません")
        return None

    try:
        results_df = pd.read_csv(results_path)
        # print(f"[{date_str}] results: {len(results_df)}件")
        odds_df = pd.read_csv(odds_path)
        odds_df = odds_df[odds_df["bet_code"] == 5]  # 三連単
        # print(f"[{date_str}] odds（三連単）: {len(odds_df)}件")

        labels = []
        for (date, venue_id, race_no), group in results_df.groupby(["date", "venue_id", "race_no"]):
            # print(f"📅 {date}, venue_id={venue_id}, R{race_no}")
            group["rank"] = pd.to_numeric(group["rank"], errors="coerce")
            ranked = group[group["rank"].isin([1, 2, 3])]
            # print(ranked[["car_no", "rank"]])
            race_no_val = group["race_no"].iloc[0]
            if ranked.shape[0] != 3:
                continue
            ranked = ranked.sort_values("rank")
            combo = tuple(ranked.sort_values("rank")["car_no"].astype(int).tolist())  # Ensure ordered by rank
            # print(f"→ rank1~3: {len(ranked)}件")
            # print(f"→ combo: {combo}")
            label = 0
            match = odds_df[
                (odds_df["venue_id"].astype(int) == int(venue_id)) &
                (odds_df["race_no"].astype(int) == int(race_no_val)) &
                (odds_df["car_1"].astype(int) == combo[0]) &
                (odds_df["car_2"].astype(int) == combo[1]) &
                (odds_df["car_3"].astype(int) == combo[2])
            ]
            # print(f"→ 該当odds: {match.shape[0]}件")
            if not match.empty and match["odds_1"].iloc[0] >= 300:
                label = 1
            labels.append({**dict(zip(["date", "venue_id", "race_no"], (date, venue_id, race_no))), "label": label})

        return pd.DataFrame(labels)

    except Exception as e:
        print(f"⚠️ {date_str} エラー: {e}")
        return None


if __name__ == "__main__":
    start_date = datetime(2022, 1, 1)
    end_date = datetime(2024, 12, 31)

    all_dfs = []
    current = start_date
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        df = extract_label_for_date(date_str)
        if df is not None and not df.empty:
            all_dfs.append(df)
        current += timedelta(days=1)

    if all_dfs:
        merged_df = pd.concat(all_dfs, ignore_index=True)
        output_path = Path("data/5th/stepA_arare_labels_2022_to_2024.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged_df.to_csv(output_path, index=False)
        print(f"✅ 出力完了: {len(merged_df)} 件 → {output_path}")
    else:
        print("⚠️ ラベルが1件も作成されませんでした。")