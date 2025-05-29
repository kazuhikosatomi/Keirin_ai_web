import duckdb
import os
from dotenv import load_dotenv

# .envからパスを読み込み
load_dotenv()
db_path = os.getenv("DUCKDB_PATH")

def delete_data_for_date(target_date):
    con = duckdb.connect(db_path)
    try:
        con.execute("DELETE FROM odds WHERE date = ?", [target_date])
        con.execute("DELETE FROM results WHERE date = ?", [target_date])
        print(f"Deleted odds and results data for {target_date}")
    finally:
        con.close()

if __name__ == "__main__":
    delete_data_for_date("2025-05-28")