import duckdb
import pandas as pd
import unicodedata

# フルパス指定
db_path = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/db/keirin_ai.duckdb"
player_path = "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/data/player/player_combined.csv"
target_date = "2025-05-21"

# DuckDB から対象データ取得
con = duckdb.connect(db_path)
df = con.execute("SELECT * FROM results_raw WHERE 日付 = ?", [target_date]).df()

# 選手名を正規化して name_key を作成
def normalize_name(name):
    if pd.isna(name):
        return ""
    name = unicodedata.normalize("NFKC", name)
    return name.replace(" ", "").replace("　", "")

df["name_key"] = df["選手名"].map(normalize_name)

# マスターデータ読み込み & 同様に name_key を生成
master = pd.read_csv(player_path, low_memory=False)
master["name_key"] = master["name"].map(normalize_name)

# マージして必要情報を補完
merged = pd.merge(df, master, on="name_key", how="left", suffixes=("", "_m"))

# スリム化された形式に変換（rankは文字列としてそのまま保存）
df_slim = pd.DataFrame({
    "date": pd.to_datetime(merged["日付"]).dt.strftime("%Y%m%d"),
    "venue_id": merged["場コード"].astype(int),
    "race_no": merged["レース"].str.replace("R", "").astype(int),
    "rank": merged["順位"],  # ← 文字列のまま保存
    "car_no": merged["車番"].astype(int),
    "name_kanji": merged["選手名"],
    "snum": merged["snum"],
    "age": merged["age"],
    "pref": merged["prefecture"],
    "grade": merged["rank"],  # ← マスターのrankをそのまま使う
    "last_time": merged["上り"],
    "finishing": merged["決まり手"],
    "diff": merged["着差"],
    "s": merged["S"],
    "b": merged["B"],
    "line_id": merged["line_id"],
    "line_pos": merged["line_pos"]
})

# テーブルがあれば削除して再作成
con.execute("DROP TABLE IF EXISTS results_slim")
con.execute("""
CREATE TABLE results_slim AS
SELECT * FROM df_slim LIMIT 0
""")

# 同日付削除後に挿入
con.execute("DELETE FROM results_slim WHERE date = ?", [target_date])
con.execute("INSERT INTO results_slim SELECT * FROM df_slim")

print(f"✅ スリム化完了: {target_date} → results_slim に保存しました")