import argparse
import pandas as pd
import os

prefecture_map_df = pd.read_csv("data/prefectures_list_with_group.csv")

def generate_features(entry_csv_path, output_csv_path):
    df = pd.read_csv(entry_csv_path)

    # area と district_group を付与
    df = df.merge(prefecture_map_df, on="prefecture", how="left")

    # line_id ごとに同一 area の比率（結束度スコア）を計算
    def compute_line_strength(sub_df):
        area_counts = sub_df["area"].value_counts()
        max_area_count = area_counts.max()
        strength_score = max_area_count / len(sub_df)
        is_temporary = 1 if max_area_count <= 2 else 0
        sub_df["line_strength_score"] = strength_score
        sub_df["is_temporary_line"] = is_temporary
        return sub_df

    df = df.groupby("line_id", group_keys=False).apply(compute_line_strength)

    # 必要な特徴量だけに絞る（学習と一致）
    features = [
        "racer_id", "car_no", "age", "win_rate",
        "style_escape", "style_sprint", "style_chase", "style_other",
        "line_pos", "line_id", "grade", "venue_id", "prefecture", "race_no", "date",
        "line_strength_score", "is_temporary_line"
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