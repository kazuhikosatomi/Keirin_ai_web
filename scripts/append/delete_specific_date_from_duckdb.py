import duckdb
import os
from dotenv import load_dotenv

# .env ファイルから DUCKDB_PATH を取得
load_dotenv()
db_path = os.getenv("DUCKDB_PATH")

# 🔧 対象日付（必要に応じて変更）
target_date = "2025-05-26"

# DuckDB に接続
con = duckdb.connect(db_path)

print(f"🧹 {target_date} の odds / results データを削除します...")

# 削除クエリ実行
con.execute(f"DELETE FROM odds WHERE date = '{target_date}'")
con.execute(f"DELETE FROM results WHERE date = '{target_date}'")

# 接続終了
con.close()

print("✅ 削除が完了しました。")