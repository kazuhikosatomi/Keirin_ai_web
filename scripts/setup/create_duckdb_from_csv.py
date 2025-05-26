import os
import duckdb
import glob
import pandas as pd

# データディレクトリ
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/data"
db_path = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/db/keirin_data.duckdb"

# DB作成（上書き）
con = duckdb.connect(database=db_path, read_only=False)

# calendar
calendar_path = os.path.join(data_dir, "calendar/calendar_all.csv")
con.execute("DROP TABLE IF EXISTS calendar")
con.execute("CREATE TABLE calendar AS SELECT * FROM read_csv_auto(?, HEADER=TRUE)", (calendar_path,))

# masterデータ
for name in ["bet_master", "player_master", "venue_master"]:
    master_path = os.path.join(data_dir, f"master/{name}.csv")
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute(f"CREATE TABLE {name} AS SELECT * FROM read_csv_auto(?, HEADER=TRUE)", (master_path,))

# odds の読み込み（複数フォルダ対応）
odds_files = glob.glob(os.path.join(data_dir, "odds", "*", "odds_*.csv"))
con.execute("DROP TABLE IF EXISTS odds")
odds_df = pd.concat([pd.read_csv(f) for f in odds_files], ignore_index=True)
con.execute("CREATE TABLE odds AS SELECT * FROM odds_df")

# results の読み込み（複数フォルダ対応）
results_files = glob.glob(os.path.join(data_dir, "results", "*", "results_*.csv"))
con.execute("DROP TABLE IF EXISTS results")
results_df = pd.concat([pd.read_csv(f) for f in results_files], ignore_index=True)
con.execute("CREATE TABLE results AS SELECT * FROM results_df")

con.close()
print(f"✅ DuckDBファイル作成完了: {db_path}")