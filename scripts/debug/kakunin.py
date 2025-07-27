import pandas as pd

# ファイルパス
csv_path = "data/8th/tmp/step1_train_data.csv"

# CSV読み込み（とりあえず最初の1万行だけ読み込み）
df = pd.read_csv(csv_path, nrows=10000)

# 10列目のカラム名を取得
col_index = 10
col_name = df.columns[col_index]
print(f"🔎 10列目のカラム名: {col_name}")

# 該当カラムのユニーク値とデータ型を確認
print("\n🧬 データ型ごとの件数:")
print(df[col_name].apply(lambda x: type(x)).value_counts())

print("\n🔢 ユニーク値の一部:")
print(df[col_name].unique()[:20])  # 最初の20個だけ表示

# 必要なら別ファイルに保存して確認
df[[col_name]].to_csv("check_column10_values.csv", index=False)
print("\n📝 該当カラムを 'check_column10_values.csv' に出力しました。")