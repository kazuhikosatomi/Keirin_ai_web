import pandas as pd
import duckdb
import datetime
import os

# 対象日を今日に設定
today = datetime.date.today().strftime('%Y-%m-%d')
print(f"🕒 append対象日: {today}")

# ファイルパス設定
csv_path = f"data/entries/{today[:4]}/entry_{today}.csv"
db_path = os.environ.get("DUCKDB_PATH") or "/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"
print(f"🛤️ 使用するDBパス: {db_path}")
print(f"📥 entry: {csv_path}")


# CSV読み込み
try:
    df = pd.read_csv(csv_path)
    # 「3.923.93」などの異常値を修正（最後の小数点だけを残す）＋ログ出力
    if 'gear' in df.columns:

        def fix_double_dot(val):
            if isinstance(val, str) and val.count('.') > 1:
                parts = val.split('.')
                return f"{parts[0]}.{parts[-1]}"
            return val

        df['gear'] = df['gear'].apply(fix_double_dot)
        df['gear'] = pd.to_numeric(df['gear'], errors='coerce')

except Exception as e:
    print(f"❌ CSV読み込み失敗: {e}")
    exit(1)

# DuckDBに接続
con = duckdb.connect(db_path)

# entryテーブルが存在しない場合は作成
create_table_sql = """
CREATE TABLE IF NOT EXISTS entry AS SELECT * FROM df LIMIT 0
"""
con.execute("INSTALL sqlite;")  # 念のため依存解決
con.execute("LOAD sqlite;")
con.execute(create_table_sql)

# 既存のデータに同じ date が存在するか確認
existing_dates = con.execute("SELECT DISTINCT date FROM entry").fetchdf()
if today in existing_dates["date"].values:
    print(f"⚠️ Entry data for {today} already exists. Skipping import.")
    con.close()
    exit(0)

# 追記
try:
    con.execute("INSERT INTO entry SELECT * FROM df")
    print(f"✅ DuckDBへの追記が完了しました（{len(df)}件）")
except Exception as e:
    print(f"❌ DuckDBへの追記に失敗: {e}")
finally:
    con.close()