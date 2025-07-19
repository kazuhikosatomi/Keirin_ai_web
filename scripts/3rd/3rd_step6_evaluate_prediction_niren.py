import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="予測対象日（例: 2020-01-01）")
args = parser.parse_args()
target_date = args.date

pred_path = f"data/3rd/step5/step5_predicted_rank_{target_date}.csv"
pred_df = pd.read_csv(pred_path)

pred_columns_to_keep = ["date", "venue_id", "race_no", "car_no", "area", "group"]
pred_df = pred_df[pred_columns_to_keep + ["predicted_rank"]]

# 予測ファイルとオッズファイルとリザルトを読み込み
odds_df = pd.read_csv(f"data/odds/{target_date[:4]}/odds_{target_date}.csv")
results_df = pd.read_csv(f"data/results/{target_date[:4]}/results_{target_date}.csv")

# ✅ 各レースで予測上位2人のcar_noを抽出 → 組み合わせ作成（順番付き）（area, groupは除去）
def get_pred_comb(df):
    top2 = df.sort_values("predicted_rank").head(2)
    top2_list = top2["car_no"].tolist()
    if len(top2_list) == 2:
        return pd.Series({
            "pred_comb": f"{top2_list[0]}-{top2_list[1]}"
        })
    return pd.Series({"pred_comb": None})

pred_combs = pred_df.groupby(["date", "venue_id", "race_no"]).apply(get_pred_comb).reset_index()

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
merged = pd.merge(
    pred_combs,
    answer_combs,
    on=["date", "venue_id", "race_no"],
    how="left"
)
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
import os
os.makedirs("data/3rd/step6", exist_ok=True)

output_path = f"data/3rd/step6/step6_evaluation_niren_{target_date}.csv"
merged.to_csv(output_path, index=False)
print(f"📤 保存完了: {output_path}")