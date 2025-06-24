import pandas as pd
from pathlib import Path
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, required=True, help="対象日（YYYY-MM-DD）")
args = parser.parse_args()
target_date = args.date

# ファイルパス
pred_path = Path(f"data/7th/tmp/step5_2_predictions_{target_date}.csv")
label_path = Path(f"data/7th/step6/step6_label_{target_date}.csv")
output_path = Path(f"data/7th/step7/step7_feedback_{target_date}.csv")

# CSV読み込み
preds = pd.read_csv(pred_path)
labels = pd.read_csv(label_path)

# マージ（キーは date + venue_id + race_no）
merged = pd.merge(preds, labels, on=["date", "venue_id", "race_no"], how="left")

# 欠損値（ラベルが存在しなかったレース）は is_arare=0 扱い
merged["is_arare"] = merged["is_arare"].fillna(0).astype(int)

# スコア順位と上位10%フラグ
merged["score_rank"] = merged["predicted_score"].rank(ascending=False, method="first")
top_threshold = int(len(merged) * 0.10)
merged["predicted_top10pct"] = merged["score_rank"] <= top_threshold

# フィードバック判定
def judge(row):
    if row["is_arare"] == 1 and row["predicted_top10pct"]:
        return "TP"
    elif row["is_arare"] == 0 and row["predicted_top10pct"]:
        return "FP"
    elif row["is_arare"] == 1 and not row["predicted_top10pct"]:
        return "FN"
    else:
        return "TN"

merged["feedback"] = merged.apply(judge, axis=1)

# 保存
output_path.parent.mkdir(parents=True, exist_ok=True)
merged.to_csv(output_path, index=False)
print(f"✅ 答え合わせ＋フィードバック結果を保存しました: {output_path}")