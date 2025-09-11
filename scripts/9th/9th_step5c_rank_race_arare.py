from datetime import datetime
import pandas as pd
import argparse

def rank_races_by_arare_score(input_path, output_path):
    df = pd.read_csv(input_path)
    print(f"📊 読み込み件数: {len(df)} 件")

    # チェック
    if "arare_score_mean" not in df.columns:
        print("❌ 'arare_score_mean' カラムが見つかりません")
        return

    # 合成スコア（mean 40%, max 30%, std 20%, min -10%）が高い順に順位をつける
    df["arare_score_combined"] = (
        0.4 * df["arare_score_mean"] +
        0.3 * df["arare_score_max"] +
        0.2 * df["arare_score_std"] -
        0.1 * df["arare_score_min"]
    )
    df["arare_rank"] = df["arare_score_combined"].rank(ascending=False, method="min").astype(int)

    # ソートして見やすく
    df = df.sort_values("arare_rank")

    # 出力
    df.to_csv(output_path, index=False)
    print(f"💾 保存完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='Date in YYYY-MM-DD format')
    args = parser.parse_args()
    if args.date:
        target_date = args.date
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 [START] 9th_step5c_rank_race_arare.py | target_date={target_date}")
    input_file = f"data/9th/step5b/step5b_predictions_race_{target_date}.csv"
    output_file = f"data/9th/step5c/step5c_predictions_ranked_{target_date}.csv"
    rank_races_by_arare_score(input_file, output_file)
    print("✅ [END] 9th_step5c_rank_race_arare.py")