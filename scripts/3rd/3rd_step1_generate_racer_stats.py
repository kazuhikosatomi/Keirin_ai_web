import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import argparse
import pandas as pd
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="Target date in YYYY-MM-DD format")
args = parser.parse_args()
target_date = pd.to_datetime(args.date)
start_date = target_date - pd.DateOffset(years=1)

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
results_df["race_grade"] = results_df["race_grade"].replace("GP", "G3")
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

# レース単位の特徴量（step0）の読み込みと結合
step0_path = Path("data/3rd/tmp/step0_race_features.csv")
if step0_path.exists():
    try:
        race_features_df = pd.read_csv(step0_path)
        # Ensure results_df has all needed columns for the join
        merge_keys = ["racer_id", "date", "venue_id", "race_no"]
        # Only keep necessary columns in results_df for merging
        results_merge_df = results_df[["racer_id", "date", "venue_id", "race_no"]]
        merged_df = pd.merge(results_merge_df, race_features_df, on=["date", "venue_id", "race_no"], how="left")
        merged_agg = merged_df.groupby("racer_id").agg(
            num_lines_mean=("num_lines", "mean"),
            num_solo_mean=("num_solo", "mean"),
            avg_line_size_mean=("avg_line_size", "mean"),
            leader_count_mean=("leader_count", "mean"),
            group_diversity_mean=("group_diversity", "mean"),
            has_cross_area_line_mean=("has_cross_area_line", "mean"),
        ).reset_index()
        agg = pd.merge(agg, merged_agg, on="racer_id", how="left")
        print("✅ step0の特徴量を選手単位に結合しました")
    except Exception as e:
        print(f"⚠️ step0の結合に失敗しました: {e}")
else:
    print("⚠️ step0_race_features.csv が見つかりませんでした")

# グレード別の勝率などを横持ちで追加
grade_list = ["F2", "F1", "G3", "G2", "G1"]
for grade in grade_list:
    sub = results_df[results_df["race_grade"] == grade]
    grade_agg = sub.groupby("racer_id").agg(
        **{
            f"win_rate_{grade}": ("rank", lambda x: (x == 1).mean()),
            f"top2_rate_{grade}": ("rank", lambda x: (x <= 2).mean()),
            f"top3_rate_{grade}": ("rank", lambda x: (x <= 3).mean()),
        }
    )
    agg = agg.merge(grade_agg, how="left", on="racer_id")
print("✅ グレード別勝率を追加しました")

# グレード別スコア（weight付き）
grade_weights = {"F2": 1.0, "F1": 1.2, "G3": 1.5, "G2": 1.8, "G1": 2.0}
agg["grade_score"] = 0.0
for grade, weight in grade_weights.items():
    rate_col = f"win_rate_{grade}"
    if rate_col in agg.columns:
        agg["grade_score"] += agg[rate_col].fillna(0) * weight
print("✅ グレードスコア（grade_score）を追加しました")

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
output_path = f"data/3rd/tmp/step1_racer_stats.csv"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
agg.to_csv(output_path, index=False)
print(f"📤 上書き保存: {output_path}")