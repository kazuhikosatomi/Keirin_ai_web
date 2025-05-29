import duckdb

def check_duckdb_counts(db_path, target_date):
    con = duckdb.connect(db_path)
    try:
        odds_count = con.execute(
            "SELECT date, COUNT(*) FROM odds WHERE date = ? GROUP BY date",
            [target_date]
        ).fetchall()
        results_count = con.execute(
            "SELECT date, COUNT(*) FROM results WHERE date = ? GROUP BY date",
            [target_date]
        ).fetchall()
        entries_count = con.execute(
            "SELECT date, COUNT(*) FROM entries WHERE date = ? GROUP BY date",
            [target_date]
        ).fetchall()
        print(f"Odds count for {target_date}: {odds_count}")
        print(f"Results count for {target_date}: {results_count}")
        print(f"Entries count for {target_date}: {entries_count}")
    finally:
        con.close()

if __name__ == "__main__":
    # DuckDBファイルのパスを適宜変更してください
    duckdb_path = "/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"
    check_date = "2025-05-28"
    check_duckdb_counts(duckdb_path, check_date)

    check_date_entry = "2025-05-29"
    check_duckdb_counts(duckdb_path, check_date_entry)