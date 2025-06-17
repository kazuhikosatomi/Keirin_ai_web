import pandas as pd
from pathlib import Path
import argparse

def main(target_date):
    # 入力ファイル（Step5の予測結果：選手単位）
    input_path = Path(f"data/5th/tmp/step5_arare_predictions.csv")
    output_path = Path(f"output/predict/5th/final_prediction_arare_{target_date}.csv")

    # Step5のCSVを読み込み
    df = pd.read_csv(input_path)

    # レース単位に集約（最大スコアを代表スコアとする）
    df_race = (
        df.groupby(["date", "venue_id", "race_no"])["arare_score"]
        .max()
        .reset_index()
    )

    # 閾値で is_arare を算出（しきい値は例として0.8）
    df_race["is_arare"] = (df_race["arare_score"] >= 0.8).astype(int)

    # venue_nameを付与
    venue_master = pd.read_csv("data/master/venue_master.csv")
    df_race = df_race.merge(venue_master[["venue_id", "venue_name"]], on="venue_id", how="left")

    # 出力項目を定義
    final_columns = [
        "date", "venue_id", "venue_name", "race_no",
        "arare_score", "is_arare"
    ]
    df_final = df_race[final_columns].copy()

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False, float_format="%.2f")
    print(f"✅ final を出力しました: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付（例: 2025-06-11）")
    args = parser.parse_args()
    main(args.date)