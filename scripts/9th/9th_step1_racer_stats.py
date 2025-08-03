import argparse
import pandas as pd
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
args = parser.parse_args()
target_date = pd.to_datetime(args.date)
target_year = target_date.year

# 結果格納用リスト
all_results = []

folder = Path(f"data/results/{target_year}")
csv_files = folder.glob("*.csv")
# 1年分に絞り込む
one_year_ago = target_date - pd.DateOffset(years=1)
all_results = []
for file in csv_files:
    df = pd.read_csv(file)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[(df["date"] >= one_year_ago) & (df["date"] < target_date)]
    all_results.append(df)

# 全部まとめて連結
results_df = pd.concat(all_results, ignore_index=True)
print(f"✅ 結合済み: {len(results_df)}件")

# 地区マスタの読み込みと prefecture を付加
pref_path = Path("data/master/prefectures_master.csv")
if pref_path.exists():
    prefectures_df = pd.read_csv(pref_path)
    prefectures_df["prefecture"] = prefectures_df["prefecture"].astype(str).str[:2]
    results_df["prefecture"] = results_df["prefecture"].astype(str).str[:2]
    if "prefecture" in results_df.columns:
        results_df = pd.merge(results_df, prefectures_df, on="prefecture", how="left")
        print("🏁 地区情報（area, group）を結合しました")
else:
    print("⚠️ prefectures_master.csv が見つかりませんでした")

# 戦法ごとのダミーフラグ列を追加
results_df["style_escape"] = (results_df["finish_tactics"] == "逃").astype(int)
results_df["style_sprint"] = (results_df["finish_tactics"] == "捲").astype(int)
results_df["style_chase"] = (results_df["finish_tactics"] == "差").astype(int)
results_df["style_other"] = (results_df["finish_tactics"] == "マ").astype(int)

# 着順の数値変換（例: '1'〜'9' を int に、LC/DS などは NaN に）
results_df["rank"] = pd.to_numeric(results_df["rank"], errors="coerce")

# 集計処理
agg = results_df.groupby("racer_id").agg(
    races=("rank", "count"),
    style_escape=("style_escape", "sum"),
    style_sprint=("style_sprint", "sum"),
    style_chase=("style_chase", "sum"),
    style_other=("style_other", "sum"),
).reset_index()

# race_grade の全角英数字を半角に変換
results_df["race_grade"] = results_df["race_grade"].astype(str).str.translate(str.maketrans({
    "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｅ": "E", "Ｆ": "F", "Ｇ": "G",
    "１": "1", "２": "2", "３": "3", "４": "4", "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
}))

# 各グレード別の勝率などを追加
for grade in ["G1", "G2", "G3", "F1", "F2"]:
    df_grade = results_df[results_df["race_grade"] == grade]
    agg_grade = df_grade.groupby("racer_id").agg(
        **{f"win_rate_{grade}": ("rank", lambda x: (x == 1).mean()),
           f"top2_rate_{grade}": ("rank", lambda x: (x <= 2).mean()),
           f"top3_rate_{grade}": ("rank", lambda x: (x <= 3).mean())}
    ).reset_index()
    agg = pd.merge(agg, agg_grade, on="racer_id", how="left")

if "area" in results_df.columns and "group" in results_df.columns:
    agg["area"] = results_df.groupby("racer_id")["area"].first().values
    agg["group"] = results_df.groupby("racer_id")["group"].first().values
    agg["prefecture"] = results_df.groupby("racer_id")["prefecture"].first().values

# 保存
output_path = f"data/9th/tmp/step1_racer_stats.csv"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
agg.to_csv(output_path, index=False)
print(f"📤 上書き保存: {output_path}")