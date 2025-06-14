import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import pandas as pd
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="予測対象日（例: 2020-01-01）")
args = parser.parse_args()
target_date = args.date

# 読み込み
pred_path = f"data/4th/tmp/step5_predicted_rank.csv"
pred_df = pd.read_csv(pred_path)
odds_df = pd.read_csv(f"data/odds/{target_date[:4]}/odds_{target_date}.csv")
results_df = pd.read_csv(f"data/results/{target_date[:4]}/results_{target_date}.csv")

# 🔹 上位3人の car_no を昇順で並べて組み合わせ文字列に変換
def get_pred_comb(df):
    top3 = df.sort_values("predicted_rank").head(3)["car_no"].tolist()
    if len(top3) == 3:
        return "-".join(map(str, sorted(top3)))
    return None

def get_answer_comb(df):
    top3 = df.sort_values("rank").head(3)["car_no"].tolist()
    if len(top3) == 3:
        return "-".join(map(str, sorted(top3)))
    return None

# 🔹 予測と実績の組み合わせ
pred_combs = pred_df.groupby(["date", "venue_id", "race_no"]).apply(get_pred_comb).reset_index(name="pred_comb")
answer_combs = results_df.groupby(["date", "venue_id", "race_no"]).apply(get_answer_comb).reset_index(name="answer_comb")

# 🔹 三連複（bet_code == 6）のオッズ処理
odds_trio = odds_df.query("bet_code == 6").copy()

# ✅ 修正後（int化 → str化 → 結合）
odds_trio["comb"] = odds_trio[["car_1", "car_2", "car_3"]].apply(lambda row: "-".join(sorted(map(lambda x: str(int(x)), row))), axis=1)

# 🔹 結合
merged = pd.merge(pred_combs, answer_combs, on=["date", "venue_id", "race_no"], how="left")
merged = pd.merge(
    merged,
    odds_trio[["date", "venue_id", "race_no", "comb", "odds_1"]],
    left_on=["date", "venue_id", "race_no", "pred_comb"],
    right_on=["date", "venue_id", "race_no", "comb"],
    how="left"
)

# 🔹 的中・払戻
merged["hit"] = (merged["pred_comb"] == merged["answer_comb"]).astype(int)
merged["payout"] = merged["hit"] * merged["odds_1"].fillna(0)

# 🔹 保存
os.makedirs("data/4th/tmp", exist_ok=True)
os.makedirs("data/4th/step6", exist_ok=True)

tmp_path = f"data/4th/tmp/4th_step6_evaluation_with_odds_trio.csv"
output_path = f"data/4th/step6/step6_evaluation_trio_{target_date}.csv"
merged.to_csv(output_path, index=False)
merged.to_csv(tmp_path, index=False)
print(f"📤 保存完了: {output_path}")