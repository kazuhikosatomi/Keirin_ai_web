
import duckdb

db_path = "/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"
con = duckdb.connect(db_path)

# ✅ 1. 各テーブルに登録されている date 一覧
print("📅 各テーブルの登録日一覧")
for table in ["odds", "results", "entry"]:
    try:
        rows = con.execute(f"SELECT DISTINCT date FROM {table} ORDER BY date DESC").fetchall()
        print(f"\n🗂 {table}:")
        for row in rows:
            print(f"  - {row[0]}")
    except Exception as e:
        print(f"⚠️ {table} → {e}")

# ✅ 2. entry テーブルのカラム情報
print("\n📊 entry テーブルのカラム情報:")
info = con.execute("PRAGMA table_info(entry);").fetchall()
for col in info:
    print(f"  - {col[1]} ({col[2]})")

# ✅ 3. entry テーブルの指定日の件数
target_date = '2025-05-30'
count = con.execute("SELECT COUNT(*) FROM entry WHERE date = ?", (target_date,)).fetchone()[0]
print(f"\n📈 entry の {target_date} 件数: {count} 件")
