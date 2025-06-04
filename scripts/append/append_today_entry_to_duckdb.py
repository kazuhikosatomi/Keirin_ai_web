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

# recent_raceカラム名を定義（1〜3行目×5列）
recent_race_cols = [f"recent_race{i}_{j}" for i in range(1, 4) for j in range(1, 6)]
dtype_map = {col: str for col in recent_race_cols}

# CSV読み込み
try:
    df = pd.read_csv(csv_path, dtype=dtype_map)
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

# entryテーブルを完全削除
try:
    con.execute("DROP TABLE IF EXISTS entry;")
    print("🗑️ 既存のentryテーブルを削除しました。")
except Exception as e:
    print(f"❌ entryテーブル削除に失敗: {e}")
    con.close()
    exit(1)

# 新しくテーブルを作成
try:
    con.execute("CREATE TABLE entry AS SELECT * FROM df")
    print(f"✅ DuckDBにentryテーブルを新規作成（{len(df)}件）")
except Exception as e:
    print(f"❌ entryテーブル作成に失敗: {e}")
finally:
    con.close()