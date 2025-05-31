import sys
import pandas as pd
import duckdb
import os

# コマンドライン引数から日付を取得
if len(sys.argv) < 2:
    print("❌ 日付を指定してください（例: 2025-05-30）")
    sys.exit(1)

target_date = sys.argv[1]
print(f"[{target_date}] 📥 Loading entry CSV")

# ファイルパス設定
csv_path = f"data/entries/{target_date[:4]}/entry_{target_date}.csv"
db_path = os.environ.get("DUCKDB_PATH") or "/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"

# CSV読み込み
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    print(f"❌ CSV読み込み失敗: {e}")
    sys.exit(1)

# DuckDBに接続
con = duckdb.connect(db_path)

# entry テーブルがなければ作成
create_table_sql = """
CREATE TABLE IF NOT EXISTS entry AS SELECT * FROM df LIMIT 0
"""
con.execute(create_table_sql)

# 既存の日付データをチェック
existing_dates = con.execute("SELECT DISTINCT date FROM entry").fetchdf()
if target_date in existing_dates["date"].values:
    existing_count = con.execute("SELECT COUNT(*) FROM entry WHERE date = ?", (target_date,)).fetchone()[0]
    print(f"[{target_date}] ⚠️ Entry data already exists ({existing_count} rows). Skipping import.")
    con.close()
    sys.exit(0)

# 追記処理
try:
    con.execute("INSERT INTO entry SELECT * FROM df")
    print(f"[{target_date}] ✅ DuckDBへの追記が完了しました（{len(df)}件）")
except Exception as e:
    print(f"[{target_date}] ❌ DuckDBへの追記に失敗: {e}")
finally:
    con.close()