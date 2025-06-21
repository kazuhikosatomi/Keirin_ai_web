import argparse
import pandas as pd
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
args = parser.parse_args()
target_date = pd.to_datetime(args.date)
start_date = target_date - pd.DateOffset(years=3)

# 結果格納用リスト
all_results = []
base_folder = Path("data/results")
for year_folder in sorted(base_folder.glob("*")):
    if not year_folder.is_dir():
        continue
    for file in sorted(year_folder.glob("results_*.csv")):
        file_date_str = file.stem.split("_")[-1]
        try:
            file_date = pd.to_datetime(file_date_str)
            if start_date <= file_date < target_date:
                df = pd.read_csv(file)
                all_results.append(df)
        except Exception:
            continue

# 全部まとめて連結
results_df = pd.concat(all_results, ignore_index=True)
print(f"✅ 結合済み: {len(results_df)}件")

# 戦法ごとのダミーフラグ列を追加
results_df["style_escape"] = (results_df["finish_tactics"] == "逃").astype(int)
results_df["style_sprint"] = (results_df["finish_tactics"] == "捲").astype(int)
results_df["style_chase"] = (results_df["finish_tactics"] == "差").astype(int)
results_df["style_other"] = (results_df["finish_tactics"] == "マ").astype(int)

# 着順の数値変換（例: '1'〜'9' を int に、LC/DS などは NaN に）
results_df["rank"] = pd.to_numeric(results_df["rank"], errors="coerce")

# 集計処理
agg = results_df.groupby("racer_id").agg(
    prefecture=("prefecture", "first"),  # 追加
    races=("rank", "count"),
    win_rate=("rank", lambda x: (x == 1).mean()),
    top2_rate=("rank", lambda x: (x <= 2).mean()),
    top3_rate=("rank", lambda x: (x <= 3).mean()),
    style_escape=("style_escape", "sum"),
    style_sprint=("style_sprint", "sum"),
    style_chase=("style_chase", "sum"),
    style_other=("style_other", "sum"),
).reset_index()

# 地区マスタの読み込みと結合
pref_path = Path("data/master/prefectures_master.csv")
if pref_path.exists():
    prefectures_df = pd.read_csv(pref_path)
    prefectures_df["prefecture"] = prefectures_df["prefecture"].astype(str).str[:2]
    agg["prefecture"] = agg["prefecture"].astype(str).str[:2]
    if "prefecture" in agg.columns:
        agg = pd.merge(agg, prefectures_df, on="prefecture", how="left")
        print("🏁 地区情報（area, group）を結合しました")
else:
    print("⚠️ prefectures_master.csv が見つかりませんでした")

# 保存
output_path = f"data/6th/tmp/step1_racer_stats.csv"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
agg.to_csv(output_path, index=False)
print(f"📤 上書き保存: {output_path}")