import pandas as pd

# 予測ファイルとオッズファイルとリザルトを読み込み
pred_df = pd.read_csv("data/2nd/predicted_rank_2020-01-01.csv")
odds_df = pd.read_csv("data/odds/2020/odds_2020-01-01.csv")
results_df = pd.read_csv("data/results/2020/results_2020-01-01.csv")

# ✅ 各レースで予測上位2人のcar_noを抽出 → 組み合わせ作成（順番付き）
def get_pred_comb(df):
    top2 = df.sort_values("predicted_rank").head(2)["car_no"].tolist()
    if len(top2) == 2:
        return f"{top2[0]}-{top2[1]}"
    return None

pred_combs = pred_df.groupby(["date", "venue_id", "race_no"]).apply(get_pred_comb).reset_index(name="pred_comb")

# ✅ 各レースの実着順上位2人のcar_noを抽出 → 組み合わせ作成（順番付き）
def get_answer_comb(df):
    top2 = df.sort_values("rank").head(2)["car_no"].tolist()
    if len(top2) == 2:
        return f"{top2[0]}-{top2[1]}"
    return None

answer_combs = results_df.groupby(["date", "venue_id", "race_no"]).apply(get_answer_comb).reset_index(name="answer_comb")

# ✅ 2車単（bet_code == 3）のオッズデータに変換（comb列追加）
odds_niren = odds_df.query("bet_code == 3").copy()
odds_niren["comb"] = odds_niren["car_1"].astype(str) + "-" + odds_niren["car_2"].astype(str)

# ✅ pred_combとanswer_combを結合 → oddsと結合
merged = pd.merge(pred_combs, answer_combs, on=["date", "venue_id", "race_no"], how="left")
merged = pd.merge(
    merged,
    odds_niren[["date", "venue_id", "race_no", "comb", "odds_1"]],
    left_on=["date", "venue_id", "race_no", "pred_comb"],
    right_on=["date", "venue_id", "race_no", "comb"],
    how="left"
)

# ✅ 的中判定と回収金額を追加
merged["hit"] = (merged["pred_comb"] == merged["answer_comb"]).astype(int)
merged["payout"] = merged["hit"] * merged["odds_1"].fillna(0)

# ✅ 保存
output_path = "data/2nd/evaluation_with_odds_2020-01-01_niren.csv"
merged.to_csv(output_path, index=False)
print(f"✅ 評価ファイルを保存しました: {output_path}")