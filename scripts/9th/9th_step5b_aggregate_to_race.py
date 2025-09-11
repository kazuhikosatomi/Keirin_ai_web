import pandas as pd
import os
import datetime
import argparse

def aggregate_racer_to_race(input_path, output_path, TODAY):
    print(f"🚀 [START] 9th_step5b_aggregate_to_race.py | target_date={TODAY}")
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
    print(f"📊 集計レース数: {len(race_df)} 件")
    print(f"📤 保存完了: {output_path}")
    print("✅ [END] 9th_step5b_aggregate_to_race.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="基準日 (YYYY-MM-DD)")
    args = parser.parse_args()
    if args.date:
        TODAY = args.date
    else:
        TODAY = datetime.date.today().strftime("%Y-%m-%d")
    input_file = f"data/9th/step5a/step5a_predictions_racer_{TODAY}.csv"
    output_file = f"data/9th/step5b/step5b_predictions_race_{TODAY}.csv"
    aggregate_racer_to_race(input_file, output_file, TODAY)