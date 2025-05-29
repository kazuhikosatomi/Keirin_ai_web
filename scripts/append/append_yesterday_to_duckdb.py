from dotenv import load_dotenv
import os

# .envの明示的な読み込み（スクリプトの2階層上）
dotenv_path = os.path.join(os.path.dirname(__file__), "../../.env")
load_dotenv(dotenv_path)

import duckdb
import pandas as pd
from datetime import datetime, timedelta

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")  # ✅ 昨日の日付（YYYY-MM-DD形式）を取得
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"🕒 append対象日: {yesterday}")
year = yesterday[:4]

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.getenv("DUCKDB_PATH")

odds_path = os.path.join(script_dir, f"../../data/odds/{year}/odds_{yesterday}.csv")
results_path = os.path.join(script_dir, f"../../data/results/{year}/results_{yesterday}.csv")

# ✅ DuckDBへ接続
print(f"🛤️ 使用するDBパス: {db_path}")
con = duckdb.connect(db_path)

# ✅ オッズを追記
if os.path.exists(odds_path):
    # 重複チェック（odds）
    check_odds = con.sql(f"SELECT COUNT(*) FROM odds WHERE date = '{yesterday}'").fetchone()[0]
    print(f"🔍 check_odds = {check_odds}")
    if check_odds > 0:
        print(f"⏩ {yesterday} の odds は既に存在します。スキップします。")
    else:
        print(f"📥 odds: {odds_path}")
        df_odds = pd.read_csv(odds_path)
        con.register("df_odds", df_odds)
        con.execute("INSERT INTO odds SELECT * FROM df_odds")
else:
    print(f"⚠️ oddsファイルが見つかりません: {odds_path}")

# ✅ リザルトを追記
if os.path.exists(results_path):
    # 重複チェック（results）
    check_results = con.sql(f"SELECT COUNT(*) FROM results WHERE date = '{yesterday}'").fetchone()[0]
    print(f"🔍 check_results = {check_results}")
    if check_results > 0:
        print(f"⏩ {yesterday} の results は既に存在します。スキップします。")
    else:
        print(f"📥 results: {results_path}")
        df_results = pd.read_csv(results_path)
        con.register("df_results", df_results)
        con.execute("INSERT INTO results SELECT * FROM df_results")
else:
    print(f"⚠️ resultsファイルが見つかりません: {results_path}")

con.close()
print("✅ DuckDBへの追記が完了しました")

log_dir = os.path.join(script_dir, "../../logs")
os.makedirs(log_dir, exist_ok=True)
log_date = datetime.now().strftime("%Y-%m-%d")
log_path = os.path.join(log_dir, f"append_daily_{log_date}.log")
with open(log_path, "a") as log_file:
    log_file.write("✅ DuckDBへの追記が完了しました\n")

import time
for filename in os.listdir(log_dir):
    if filename.startswith("append_daily_") and filename.endswith(".log"):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            if time.time() - file_mtime > 30 * 86400:
                os.remove(filepath)