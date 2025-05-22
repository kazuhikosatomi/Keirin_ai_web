import duckdb
import pandas as pd

# CSVとDBのパス（必要に応じて変更）
csv_path = "chariloto_results_2025-05-21.csv"
db_path = "../db/keirin_ai.duckdb"  # または絶対パスにする

# CSV読み込み
df = pd.read_csv(csv_path)

# 対象日付の抽出（最初の1行の"日付"列）
target_date = df["日付"].iloc[0]

# DuckDBに接続
con = duckdb.connect(database=db_path)

# テーブルがなければ作成（初回のみ）
con.execute("""
CREATE TABLE IF NOT EXISTS results_raw AS
SELECT * FROM df LIMIT 0
""")

# 同じ日付のデータがあれば削除してから追加
con.execute("DELETE FROM results_raw WHERE 日付 = ?", [target_date])
con.execute("INSERT INTO results_raw SELECT * FROM df")

print(f"✅ {target_date} のレース結果を results_raw に登録しました")