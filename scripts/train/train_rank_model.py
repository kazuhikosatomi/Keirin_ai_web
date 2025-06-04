import argparse
import pandas as pd
from pathlib import Path

def load_data(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path, dtype=str)

    # 不可視文字・全角スペース・空白削除
    df["date"] = df["date"].str.replace(r"[　\u200b\s]", "", regex=True)

    # datetime64[ns] に変換
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # エラー確認用の出力
    if df["date"].isna().any():
        print("❗ 日付変換に失敗した行があります（先頭5件）:")
        print(df[df["date"].isna()][["date"]].head())

    print("✅ date変換後のサンプル:", df["date"].head())
    print("📅 df['date'] min-max:", df["date"].min(), "-", df["date"].max())

    return df

def filter_by_date(df: pd.DataFrame, train_until: str) -> pd.DataFrame:
    cutoff = pd.to_datetime(train_until)
    print("🧪 train_until:", cutoff)
    df_filtered = df[df["date"] < cutoff]
    if df_filtered.empty:
        print("❌ フィルター後のデータが存在しません。train_until の日付を確認してください。")
    else:
        print("✅ フィルター後の件数:", len(df_filtered))
    return df_filtered

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_until", type=str, required=True)
    args = parser.parse_args()

    csv_path = Path("data/train/train_racer_level.csv")
    if not csv_path.exists():
        print("❌ 入力ファイルが見つかりません:", csv_path)
        return

    df = load_data(str(csv_path))
    df_filtered = filter_by_date(df, args.train_until)

    # 必要があれば、ここに保存や学習処理を追加
    # 例: df_filtered.to_csv("filtered_train_data.csv", index=False)

if __name__ == "__main__":
    main()