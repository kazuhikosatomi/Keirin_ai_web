import pandas as pd

# ファイルパス（必要に応じて修正）
file_path = "data/8th/tmp/step1_train_data.csv"

# 最初の数行のみ読み込む（カラムだけ取得）
df = pd.read_csv(file_path, nrows=5)

# カラム一覧を出力
print("🔍 カラム一覧:")
print(df.columns.tolist())