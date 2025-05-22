import duckdb
import pandas as pd

# 対象日付
target_date = "2025-05-21"

# DuckDB パス
db_path = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/db/keirin_ai.duckdb"

# DuckDB 接続
con = duckdb.connect(db_path)

# odds_raw から該当日付のデータ取得（注意：日付は日本語カラム）
df = con.execute("SELECT * FROM odds_raw WHERE 日付 = ?", [target_date]).df()

# カラム名を英語に変換（存在するもののみ）
df = df.rename(columns={
    "日付": "date",
    "場名": "venue_name",
    "場コード": "venue_id",
    "レース": "race_no",
    "賭式": "buy_type",
    "組番": "combination",
    "オッズ": "odds"
})

# race_no を "1R" → 1 のように数値化
df["race_no"] = df["race_no"].astype(str).str.replace("R", "", regex=False).astype(int)

buy_type_map = {
    "niwakutan": 1,
    "niwakufuku": 2,
    "nirentan": 3,
    "nirenfuku": 4,
    "sanrentan": 5,
    "sanrenfuku": 6,
    "wide": 7
}
df["buy_type"] = df["buy_type"].map(buy_type_map)

# 組番を car1, car2, car3 に安全に分割
car_cols = df["combination"].fillna("").astype(str).str.split("-", expand=True)
df["car1"] = car_cols[0] if car_cols.shape[1] > 0 else None
df["car2"] = car_cols[1] if car_cols.shape[1] > 1 else None
df["car3"] = car_cols[2] if car_cols.shape[1] > 2 else None

# スリム化（存在するカラムのみに限定）
df_slim = df[[
    "date", "venue_id", "race_no",
    "buy_type", "car1", "car2", "car3", "odds"
]]

# DuckDBにテーブル登録して保存
con.register("df_slim", df_slim)
con.execute("DROP TABLE IF EXISTS odds_slim")
con.execute("CREATE TABLE odds_slim AS SELECT * FROM df_slim")

print(f"✅ スリム化完了: {target_date} → odds_slim に保存しました")