import duckdb

def check_table_count(conn, table_name, target_date):
    query = f"SELECT COUNT(*) FROM {table_name} WHERE date = ?"
    result = conn.execute(query, (target_date,)).fetchone()
    count = result[0]
    print(f"🎯 {table_name} {target_date}: {count} 件")

    try:
        distinct_dates = conn.execute(f"SELECT DISTINCT date FROM {table_name} ORDER BY date DESC").fetchall()
        print(f"📅 登録されている date 一覧:")
        for d in distinct_dates:
            print(f"  - {d[0]}")
    except Exception:
        pass

# 🔧 個別に日付を指定
date_odds = "2025-05-29"
date_results = "2025-05-29"
date_entry = "2025-05-31"

# DuckDBへの接続
db_path = "/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"
con = duckdb.connect(db_path)

# 🔍 各テーブルの件数を取得
try:
    check_table_count(con, "odds", date_odds)
except Exception as e:
    print(f"❌ odds の取得に失敗しました: {e}")

try:
    check_table_count(con, "results", date_results)
except Exception as e:
    print(f"❌ results の取得に失敗しました: {e}")

try:
    check_table_count(con, "entry", date_entry)
except Exception as e:
    print(f"❌ entry の取得に失敗しました: {e}")