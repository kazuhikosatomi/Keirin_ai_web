import pandas as pd

# 読み込み：resultsをentryと見立てる
df_entry = pd.read_csv("data/results/2020/results_2020-01-01.csv")

# 読み込み：racerごとの過去成績（step1の出力）
df_stats = pd.read_csv("data/2nd/racer_stats_2025_2029.csv")

# 不要なカラムを削除（entry_likeとして必要なものだけ残す）
df_entry = df_entry[[
    "racer_id", "date", "car_no", "line_pos", "line_id", "grade",
    "venue_id", "prefecture", "race_no", "age"
]]

# 結合：選手IDで過去成績をマージ
df_entry_like = pd.merge(df_entry, df_stats, on="racer_id", how="left")

# rank列は除外（予測対象のため）
if "rank" in df_entry_like.columns:
    df_entry_like = df_entry_like.drop(columns=["rank"])

# 保存
df_entry_like.to_csv("data/2nd/entry_like_2020-01-01.csv", index=False)
print("✅ entry_likeファイルの保存完了: data/2nd/entry_like_2020-01-01.csv")