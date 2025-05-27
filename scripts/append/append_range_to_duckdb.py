from dotenv import load_dotenv
import os

# .env のフルパスをスクリプト基準で指定して読み込む
dotenv_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path)
import os
import duckdb
import pandas as pd
from datetime import datetime, timedelta
import argparse

# ✅ 引数で期間指定
parser = argparse.ArgumentParser()
parser.add_argument("start", help="開始日付 (YYYY-MM-DD)")
parser.add_argument("end", help="終了日付 (YYYY-MM-DD)")
args = parser.parse_args()

start_date = args.start
end_date = args.end

try:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
except ValueError:
    print("日付形式が正しくありません（YYYY-MM-DD）")
    exit(1)

# ✅ ベースパス設定
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.getenv("DUCKDB_PATH")

# ✅ DuckDB接続
con = duckdb.connect(db_path)

# ✅ 期間ループ処理
current = start_dt
while current <= end_dt:
    date_str = current.strftime("%Y-%m-%d")
    year = date_str[:4]

    odds_path = os.path.join(script_dir, f"../../data/odds/{year}/odds_{date_str}.csv")
    results_path = os.path.join(script_dir, f"../../data/results/{year}/results_{date_str}.csv")

    if os.path.exists(odds_path):
        print(f"📥 odds: {odds_path}")
        df_odds = pd.read_csv(odds_path)
        exists = con.execute(f"SELECT COUNT(*) FROM odds WHERE date = '{date_str}'").fetchone()[0]
        if exists:
            print(f"⏩ {date_str} の odds は既に存在します。スキップします。")
        else:
            con.execute("INSERT INTO odds SELECT * FROM df_odds")
    else:
        print(f"⚠️ oddsファイル未検出: {odds_path}")

    if os.path.exists(results_path):
        print(f"📥 results: {results_path}")
        df_results = pd.read_csv(results_path)
        exists = con.execute(f"SELECT COUNT(*) FROM results WHERE date = '{date_str}'").fetchone()[0]
        if exists:
            print(f"⏩ {date_str} の results は既に存在します。スキップします。")
        else:
            con.execute("INSERT INTO results SELECT * FROM df_results")
    else:
        print(f"⚠️ resultsファイル未検出: {results_path}")

    current += timedelta(days=1)

con.close()

# --- 日付付きログ出力 ---
log_dir = os.path.join(script_dir, "../../logs")
os.makedirs(log_dir, exist_ok=True)
log_date = datetime.now().strftime("%Y-%m-%d")
log_path = os.path.join(log_dir, f"append_range_{log_date}.log")
with open(log_path, "a") as log_file:
    log_file.write(f"✅ DuckDBへの複数日追記が完了しました ({start_date}〜{end_date})\n")

# --- 30日以上前のログファイル削除 ---
import time
for filename in os.listdir(log_dir):
    if filename.startswith("append_range_") and filename.endswith(".log"):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            if time.time() - file_mtime > 30 * 86400:
                os.remove(filepath)

print("✅ DuckDBへの複数日追記が完了しました")