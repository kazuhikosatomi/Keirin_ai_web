import argparse
import pandas as pd
from pathlib import Path

def load_csv(path):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    return df

def evaluate_exacta(pred_df, odds_df, result_df):
    merged = pred_df.merge(result_df[["race_no", "racer_id", "rank"]], on=["race_no", "racer_id"], how="left")

    print("🧪 merged.columns =", merged.columns.tolist())
    print("🧪 merged.head() =")
    print(merged.head())
    
    evaluations = []
    for race_no, group in merged.groupby("race_no"):
        # 予測上位2人
        top2 = group.sort_values("predicted_rank").head(2)
        if len(top2) < 2 or top2["rank_y"].isna().any():
            continue
        
        pred_1 = top2.iloc[0]
        pred_2 = top2.iloc[1]
        
        pred_comb1 = int(pred_1["car_no"])
        pred_comb2 = int(pred_2["car_no"])

        # 実際の1着・2着
        actual_top2 = group[group["rank_y"].isin([1, 2])].sort_values("rank_y")
        if len(actual_top2) < 2:
            continue

        actual_1 = int(actual_top2.iloc[0]["car_no"])
        actual_2 = int(actual_top2.iloc[1]["car_no"])

        # 的中判定（順番あり）
        is_hit = (pred_comb1 == actual_1 and pred_comb2 == actual_2)

        # 配当取得（bet_code 3 = 2車単）
        odds_row = odds_df[
            (odds_df["race_no"] == race_no) &
            (odds_df["bet_code"] == 3) &
            (odds_df["comb1"] == pred_comb1) &
            (odds_df["comb2"] == pred_comb2)
        ]

        payout = odds_row["pay"].values[0] if is_hit and not odds_row.empty else 0

        evaluations.append({
            "race_no": race_no,
            "pred_comb1": pred_comb1,
            "pred_comb2": pred_comb2,
            "actual_comb1": actual_1,
            "actual_comb2": actual_2,
            "hit": is_hit,
            "payout": payout
        })

    return pd.DataFrame(evaluations)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predicted", required=True)
    parser.add_argument("--odds", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pred_df = load_csv(args.predicted)
    odds_df = load_csv(args.odds)
    result_df = load_csv(args.results)

    print("📝 2車単評価中...")
    eval_df = evaluate_exacta(pred_df, odds_df, result_df)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    eval_df.to_csv(args.output, index=False)
    print(f"✅ 評価結果保存完了: {args.output}")