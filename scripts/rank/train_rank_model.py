import argparse
import pandas as pd
from pathlib import Path
import lightgbm as lgb
import pickle

def load_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)

    print("✅ データ読み込み完了:", file_path)
    print("📊 レコード数:", len(df))
    print("📋 カラム一覧:", list(df.columns))

    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_file", type=str, required=True, help="学習用CSVファイルのパス")
    args = parser.parse_args()

    csv_path = Path(args.train_file)
    if not csv_path.exists():
        print("❌ 指定されたファイルが見つかりません:", csv_path)
        return

    # Load entry and stats data, merge on racer_id
    df_entry = pd.read_csv("data/train/entry_like_2020-01-01.csv")
    df_stats = pd.read_csv("data/train/train_racer_level.csv")
    df = df_entry.merge(df_stats, on="racer_id", how="left")

    if "rank" not in df.columns:
        print("❌ 'rank' カラムが存在しません。目的変数が必要です。")
        return

    # rankを数値化（例: 1着=1, 2着=2, …）
    df = df[df["rank"].notna()]
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df = df[df["rank"].notna()]
    df["rank"] = df["rank"].astype(int)

    X = df.drop(columns=["rank"])
    y = df["rank"]

    print(f"🧬 使用特徴量一覧: {list(X.columns)}")
    print("🧪 欠損のあるカラム:")
    print(X.isna().sum()[X.isna().sum() > 0])

    model = lgb.LGBMClassifier(random_state=42)
    model.fit(X, y)

    output_path = Path("models/rank_model.pkl")
    with open(output_path, "wb") as f:
        pickle.dump(model, f)
    print("✅ モデル保存完了:", output_path)

if __name__ == "__main__":
    main()