import pandas as pd
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="評価CSVファイルのパス")
    parser.add_argument("--output-dir", required=True, help="保存先ディレクトリ")
    parser.add_argument("--date", required=True, help="対象日付（例: 2020-01-01）")
    args = parser.parse_args()

    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(args.output_dir, exist_ok=True)

    # 評価CSVを読み込み
    df = pd.read_csv(args.input)

    # 保存先パスを構築
    output_path = os.path.join(args.output_dir, f"evaluation_{args.date}.csv")

    # CSVを保存
    df.to_csv(output_path, index=False)

    print(f"✅ 評価CSVを保存しました: {output_path}")