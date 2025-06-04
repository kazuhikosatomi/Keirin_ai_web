import pandas as pd

# ファイルパス
csv_path = "data/train/train_racer_level.csv"

# CSV読み込み
df = pd.read_csv(csv_path)

# dateカラムをdatetime64[ns]型に変換（エラーはNaTに）
df["date"] = pd.to_datetime(df["date"], errors='coerce')

# NaTがある場合の警告（任意）
num_nat = df["date"].isna().sum()
if num_nat > 0:
    print(f"⚠️ 'date'列に変換できない値が {num_nat} 件ありました（NaTに変換）")

# 上書き保存（インデックス列は出力しない）
df.to_csv(csv_path, index=False)
print("✅ 'date'列を datetime64[ns] に変換し、CSVに保存しました")