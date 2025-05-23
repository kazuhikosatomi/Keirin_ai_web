import duckdb
import pandas as pd
import os
import argparse

# 引数パーサー設定
parser = argparse.ArgumentParser(description='Insert odds raw data into DuckDB.')
parser.add_argument('--target', type=str, required=True, help='対象日付 (YYYY-MM-DD)')
args = parser.parse_args()

# 対象日付
target_date = args.target
short_date = target_date.replace("-", "")

# ファイルパス
csv_path = f"/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/chariloto_odds_{target_date}.csv"
db_path = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/db/keirin_ai.duckdb"

# ファイル存在チェック
if not os.path.exists(csv_path):
    raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_path}")

# 読み込み
df = pd.read_csv(csv_path)

# DuckDBに接続
con = duckdb.connect(db_path)

# テーブルがなければ作成（dfの構造を元に）
con.execute("""
CREATE TABLE IF NOT EXISTS odds_raw AS
SELECT * FROM df LIMIT 0
""")

# 同日削除 → 追記
con.execute("DELETE FROM odds_raw WHERE 日付 = ?", [int(short_date)])
con.execute("INSERT INTO odds_raw SELECT * FROM df")

print(f"✅ odds_raw に保存完了: {target_date}（{len(df)} 件）")