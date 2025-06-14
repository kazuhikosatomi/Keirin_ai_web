import argparse
import pandas as pd
from pathlib import Path

def main(prediction_path):
    if not Path(prediction_path).exists():
        print(f"[ERROR] ファイルが存在しません: {prediction_path}")
        return

    df = pd.read_csv(prediction_path)
    if df.empty:
        print("[INFO] ファイルは空です")
        return

    print("📊【三連複】予測結果プレビュー")
    for _, row in df.iterrows():
        date = row.get("date", "不明")
        venue = row.get("venue_name") or row.get("venue_id", "不明")
        race_no = int(row.get("race_no", -1))
        combo = row.get("comb", "不明")
        score = row.get("score", None)

        if pd.notna(score):
            line = f"{date} {venue} {race_no}R：{combo}（スコア: {score:.2f}）"
        else:
            line = f"{date} {venue} {race_no}R：{combo}"
        print(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="三連複予測CSVファイルのパス")
    args = parser.parse_args()

    main(args.file)