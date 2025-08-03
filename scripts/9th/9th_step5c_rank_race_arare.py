import pandas as pd

def rank_races_by_arare_score(input_path, output_path):
    df = pd.read_csv(input_path)

    # チェック
    if "arare_score_mean" not in df.columns:
        print("❌ 'arare_score_mean' カラムが見つかりません")
        return

    # 合成スコア（mean 70%, max 30%）が高い順に順位をつける
    if "arare_score_max" in df.columns:
        df["arare_score_combined"] = (
            0.7 * df["arare_score_mean"] + 0.3 * df["arare_score_max"]
        )
        df["arare_rank"] = df["arare_score_combined"].rank(ascending=False, method="min").astype(int)
    else:
        df["arare_rank"] = df["arare_score_mean"].rank(ascending=False, method="min").astype(int)

    # ソートして見やすく
    df = df.sort_values("arare_rank")

    # 出力
    df.to_csv(output_path, index=False)
    print(f"📤 出力完了: {output_path}")

if __name__ == "__main__":
    input_file = "data/9th/tmp/step5b_predictions_race.csv"
    output_file = "data/9th/tmp/step5c_predictions_ranked.csv"
    rank_races_by_arare_score(input_file, output_file)