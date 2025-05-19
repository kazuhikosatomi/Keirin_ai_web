import duckdb

# DuckDBファイルに接続（ファイルパスを合わせてください）
con = duckdb.connect("/Users/satomi/Documents/keirin_ai/keirin_ai.duckdb")

# CSVの読み込みとテーブル作成（上書きOK）
con.execute("""
CREATE OR REPLACE TABLE keirin_places AS
SELECT * FROM read_csv_auto('/Users/satomi/Documents/keirin_ai/data/venue/jyocode.csv')
""")

# テスト表示
df = con.execute("SELECT * FROM keirin_places LIMIT 5").fetchdf()
print(df)