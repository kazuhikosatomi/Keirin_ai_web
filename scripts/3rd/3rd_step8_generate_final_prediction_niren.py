import pandas as pd
from pathlib import Path
import argparse

def main(target_date):
    # 3rdステップ用にパスを変更
    # 入力ファイルパス（Step5の予測結果）
    input_path = Path(f"data/3rd/step5/step5_predicted_rank_{target_date}.csv")
    output_path = Path(f"docs/predict/csv/3rd/final_prediction_niren_{target_date}.csv")

    # Step5の予測CSVを読み込み
    df = pd.read_csv(input_path)

    if "name_kanji_x" in df.columns:
        df = df.rename(columns={"name_kanji_x": "name_kanji"})

    # 必要な列だけ抽出（racer_idを追加）
    expected_columns = [
        "date", "venue_id", "race_grade", "race_no",
        "predicted_rank", "car_no", "racer_id", "name_kanji", "prefecture", "predicted_score", "grade"
    ]

    # 不足カラムは空で作成（特に racer_id を保証）
    missing = []
    for col in expected_columns:
        if col not in df.columns:
            df[col] = None
            missing.append(col)
    if "racer_id" in missing:
        print("⚠️ 'racer_id' が入力に存在しませんでした。空欄で出力します。")

    # predicted_scoreを安全に数値へ → 小数第2位文字列
    df["predicted_score"] = pd.to_numeric(df["predicted_score"], errors="coerce")
    df["predicted_score"] = df["predicted_score"].apply(lambda x: "{:.2f}".format(x if pd.notna(x) else 0.0))

    # predicted_rankは整数へ（四捨五入）
    df["predicted_rank"] = pd.to_numeric(df["predicted_rank"], errors="coerce").round().astype("Int64").astype(object)
    df["predicted_rank"] = df["predicted_rank"].apply(lambda v: int(v) if pd.notna(v) else None)

    if "grade" not in df.columns:
        df["grade"] = ""

    df_final = df[expected_columns].copy()

    # venue_masterを読み込み、venue_nameを取得
    venue_master = pd.read_csv("data/master/venue_master.csv")

    # venue_idに基づいて venue_name を付与
    df_final = df_final.merge(venue_master[["venue_id", "venue_name"]], on="venue_id", how="left")

    final_columns = [
        "date", "venue_id", "venue_name", "race_grade", "race_no",
        "predicted_rank", "car_no", "racer_id", "name_kanji", "prefecture", "predicted_score", "grade"
    ]
    df_final = df_final[final_columns]

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False)
    print(f"✅ final を出力しました: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付（例: 2025-06-11）")
    args = parser.parse_args()
    main(args.date)