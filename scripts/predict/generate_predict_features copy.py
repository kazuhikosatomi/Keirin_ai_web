import argparse
import pandas as pd
import os

def generate_features(entry_csv_path, output_csv_path):
    df = pd.read_csv(entry_csv_path)

    # 必要な特徴量だけに絞る（学習と一致）
    features = [
        "racer_id", "car_no", "age", "win_rate",
        "style_escape", "style_sprint", "style_chase", "style_other",
        "line_pos", "line_id", "grade", "venue_id", "prefecture", "race_no", "date"
    ]

    df = df[features]
    df.to_csv(output_csv_path, index=False)
    print(f"✅ 特徴量CSV出力完了: {output_csv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="出走表の日付 (YYYY-MM-DD)")
    args = parser.parse_args()

    entry_csv = f"data/entries/2025/entry_{args.date}.csv"
    output_csv = f"data/train/predict_features_{args.date}.csv"

    if not os.path.exists(entry_csv):
        raise FileNotFoundError(f"❌ 出走表が見つかりません: {entry_csv}")

    generate_features(entry_csv, output_csv)