import os
import duckdb
import pandas as pd
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# ▼ 今日の日付を取得（YYYY-MM-DD 形式）
today_str = date.today().strftime("%Y-%m-%d")
year_str = date.today().strftime("%Y")
print(f"🕒 append対象日: {today_str}")

# ▼ DuckDBのパス（必要に応じて変更）
db_path = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb"
)
print(f"🛤️ 使用するDBパス: {db_path}")

# ▼ 出走表CSVのパスを組み立て
entry_csv_path = BASE_DIR / f"data/entries/{year_str}/entry_{today_str}.csv"
print(f"📥 entry: {entry_csv_path.resolve()}")

if not os.path.exists(entry_csv_path):
    print("⚠️ 出走表ファイルが存在しません。処理をスキップします。")
    exit()

# ▼ DuckDBに接続
con = duckdb.connect(db_path)

# ▼ entries テーブルが存在するかチェック
table_exists = con.execute(
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'entries'"
).fetchone()[0] > 0

# ▼ 既存データに同日データが存在するかチェック（テーブルが存在する場合のみ）
if table_exists:
    check_entry = con.execute(
        f"SELECT COUNT(*) FROM entries WHERE date = '{today_str}'"
    ).fetchone()[0]

    if check_entry > 0:
        print("⏭️ すでに同日の出走表データが存在するためスキップします。")
        exit()

# ▼ CSVファイルを読み込む
df = pd.read_csv(str(entry_csv_path), dtype=str).fillna("")

# ▼ "date" カラムがなければ追加（ファイル名から補完）
if "date" not in df.columns:
    df["date"] = today_str

# ▼ 必要であれば列順を固定
column_order = [
    "date", "venue_id", "race_no", "car_no", "frame_no", "racer_id",
    "name_kanji", "style", "age", "recent_place1", "recent_place2", "recent_place3",
    "recent_date1", "recent_date2", "recent_date3",
    "line_id", "line_pos", "line_name", "sex", "hometown", "team"
]
df = df[[col for col in column_order if col in df.columns]]

# ▼ データ型変換（必要に応じて）
df["race_no"] = df["race_no"].astype(int)
df["car_no"] = df["car_no"].astype(int)

# ▼ DuckDBに追記
con.execute("CREATE TABLE IF NOT EXISTS entries AS SELECT * FROM df LIMIT 0")
con.execute("INSERT INTO entries SELECT * FROM df")
print(f"✅ DuckDBへの追記が完了しました（{len(df)}件）")

con.close()