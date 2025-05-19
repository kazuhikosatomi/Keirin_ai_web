import duckdb
import os
import pandas as pd

conn = duckdb.connect("keirin_ai.duckdb")

def import_csv_if_new(csv_path, table_name, key_columns):
    df = pd.read_csv(csv_path)

    if not all(k in df.columns for k in key_columns):
        print(f"⚠️ {csv_path} は必要なキー列がありません → スキップ")
        return

    try:
        existing_keys = set(conn.execute(
            f"SELECT {','.join(key_columns)} FROM {table_name}"
        ).fetchall())
    except Exception:
        existing_keys = set()

    new_rows = []
    for _, row in df.iterrows():
        key = tuple(row[k] for k in key_columns)
        if key not in existing_keys:
            new_rows.append(row)

    if new_rows:
        df_new = pd.DataFrame(new_rows)
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df_new LIMIT 0")
        conn.register("df_new", df_new)
        conn.execute(f"INSERT INTO {table_name} SELECT * FROM df_new")
        print(f"✅ 登録: {csv_path} → {len(new_rows)} 件追加")
    else:
        print(f"⏭️ スキップ: {csv_path}（すべて既存）")

total_files = 0
for data_dir, table_name, keys in [
    ("data/odds", "odds", ["date", "venue_id", "race_no"]),
    ("data/results", "results", ["date", "venue_id", "race_no"])
]:
    print(f"📂 処理対象: {data_dir} → {table_name}")
    for root, _, files in os.walk(data_dir):
        for file in sorted(files):
            if file.endswith(".csv"):
                total_files += 1
                path = os.path.join(root, file)
                import_csv_if_new(path, table_name, keys)

print(f"🔚 全処理完了（対象ファイル数: {total_files}）")