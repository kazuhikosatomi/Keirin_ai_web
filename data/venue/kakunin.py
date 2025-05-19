import duckdb
import pandas as pd

# DuckDBに接続
con = duckdb.connect("/Users/satomi/Documents/keirin_ai/keirin_ai.duckdb")

# テーブルから全件取得
df = con.execute("SELECT * FROM keirin_places").fetchdf()

# CSVに保存（パスはお好みで）
output_path = "/Users/satomi/Documents/keirin_ai/data/venue/keirin_places_export.csv"
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ CSV出力完了: {output_path}")