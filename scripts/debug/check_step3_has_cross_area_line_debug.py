import pandas as pd

# 🔁 ファイルパスは適宜変更してください
entry_path = "data/entries/2025/entry_2025-07-27.csv"

# CSV読み込み（エンコーディング対策含む）
try:
    df = pd.read_csv(entry_path, encoding="utf-8")
except UnicodeDecodeError:
    df = pd.read_csv(entry_path, encoding="shift_jis")

# 🔍 area列が存在するか確認
if "area" not in df.columns:
    print("❌ 'area' カラムが見つかりません。'prefecture' カラムから変換されているか確認してください。")
    print("🔍 現在のカラム一覧:", df.columns.tolist())
    exit()

# 🔍 各種チェック
print("✅ area カラムのユニーク値:", df["area"].dropna().unique())
print("✅ area 欠損数:", df["area"].isnull().sum())

if "line_pos" not in df.columns:
    print("❌ 'line_pos' カラムが見つかりません。")
else:
    print("✅ line_pos ユニーク値:", df["line_pos"].dropna().unique())
    print("✅ line_pos==1 のデータ件数:", df[df["line_pos"] == 1].shape[0])

if "line_id" in df.columns:
    try:
        print("\n✅ line_id ごとの先頭選手 (line_pos==1) のエリア数:")
        print(
            df[df["line_pos"] == 1].groupby("line_id")["area"].nunique()
        )
    except Exception as e:
        print("⚠️ line_id 分析中にエラー:", e)
else:
    print("❌ 'line_id' カラムが見つかりません。")

print("\n✅ prefecture → area のサンプル:")
print(df[["racer_id", "prefecture", "area"]].drop_duplicates().head(10))