import pandas as pd
import os

def aggregate_racer_to_race(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"❌ 入力ファイルが見つかりません: {input_path}")
        return

    # データ読み込み
    df = pd.read_csv(input_path)

    # 必要なカラムがあるか確認
    required_cols = {"date", "venue_id", "race_no", "arare_score"}
    if not required_cols.issubset(df.columns):
        print(f"❌ 必要なカラムが不足しています: {required_cols - set(df.columns)}")
        return

    # レース単位で集計（平均・最大・標準偏差など）
    race_df = df.groupby(["date", "venue_id", "race_no"]).agg(
        num_racers=("arare_score", "count"),
        arare_score_mean=("arare_score", "mean"),
        arare_score_max=("arare_score", "max"),
        arare_score_min=("arare_score", "min"),
        arare_score_std=("arare_score", "std"),
    ).reset_index()

    # 出力
    race_df.to_csv(output_path, index=False)
    print(f"📤 出力完了: {output_path}")


if __name__ == "__main__":
    input_file = "data/9th/tmp/step5a_predictions_racer.csv"
    output_file = "data/9th/tmp/step5b_predictions_race.csv"
    aggregate_racer_to_race(input_file, output_file)