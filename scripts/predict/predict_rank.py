import argparse
import pandas as pd
import joblib
import os
import datetime

def predict(date):
    # パス設定
    model_path = "models/rank_predict_model.pkl"
    feature_path = f"data/train/predict_features_{date}.csv"
    output_path = f"output/predict/train.predicted_rank_{date}.csv"

    # モデルと特徴量の読み込み
    model = joblib.load(model_path)
    df = pd.read_csv(feature_path)

    df["grade"] = df["grade"].astype("category").cat.codes
    df["prefecture"] = df["prefecture"].astype("category").cat.codes
    df["date"] = pd.to_datetime(df["date"])
    df["date_ts"] = df["date"].astype("int64") // 10**9

    # ID列などを保持しておく
    if "race_id" in df.columns:
        id_cols = df[["race_id", "car_no"]]
    else:
        id_cols = df[["race_no", "venue_id", "date", "car_no"]]

    # 予測対象の特徴量（rankなど除く）
    feature_cols = ["racer_id", "car_no", "age", "win_rate",
                    "style_escape", "style_sprint", "style_chase", "style_other",
                    "line_pos", "line_id", "grade", "venue_id", "prefecture", "race_no", "date_ts"]
    X = df[feature_cols]

    # 予測
    df["predicted_rank"] = model.predict(X)
    df["predicted_rank"] = df["predicted_rank"].map(lambda x: f"{x:.2f}")

    df["rank_within_race"] = df.groupby(["date", "venue_id", "race_no"])["predicted_rank"].rank(method="min").astype(int)

    # 出力用にまとめる
    output_df = pd.concat([id_cols, df[["predicted_rank", "rank_within_race"]]], axis=1)

    # venue_masterからvenue_nameを取得
    venue_master = pd.read_csv("data/master/venue_master.csv")
    output_df = pd.merge(output_df, venue_master, on="venue_id", how="left")

    # 出走表から選手名を取得して追加
    entry_path = f"data/entries/{date[:4]}/entry_{date}.csv"
    entry_df = pd.read_csv(entry_path)
    entry_df["date"] = pd.to_datetime(entry_df["date"])
    output_df = pd.merge(output_df, entry_df[["date", "venue_id", "race_no", "car_no", "name_kanji"]],
                         on=["date", "venue_id", "race_no", "car_no"], how="left")

    # 欲しい順に並び替え
    output_df = output_df[["date", "venue_id", "venue_name", "race_no", "rank_within_race", "car_no", "name_kanji", "predicted_rank"]]

    output_df = output_df.sort_values(by=["date", "venue_id", "race_no", "rank_within_race"])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_df.to_csv(output_path, index=False)
    print(f"✅ 予測結果を出力しました: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付（例: 2025-06-01）")
    args = parser.parse_args()
    predict(args.date)