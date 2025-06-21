import pandas as pd
import argparse
from datetime import datetime, timedelta
from pathlib import Path

RESULTS_DIR = Path("data/results")
EVAL_DIR = Path("data/1st")
OUTPUT_PATH = Path("data/1st/step7")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="日付 (YYYY-MM-DD)")
    return parser.parse_args()

def main():
    args = parse_args()
    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    prev_date = target_date - timedelta(days=1)

    eval_path = f"data/1st/step6/step6_evaluation_niren_{target_date}.csv"
    result_path = f"data/results/{str(target_date.year)}/results_{target_date}.csv"

    eval_file = Path(eval_path)
    result_file = Path(result_path)

    if not eval_file.exists() or not result_file.exists():
        print("⚠️ 評価ファイルまたは結果ファイルが見つかりません")
        return

    print(f"📥 評価ファイル読み込み: {eval_path}")
    print(f"📥 結果ファイル: {result_path}")

    eval_df = pd.read_csv(eval_file)
    results_df = pd.read_csv(result_file)

    # 的中判定列（的中:1, 不的中:0）
    eval_df["hit"] = (eval_df["pred_comb"] == eval_df["answer_comb"]).astype(int)

    # car1, car2 を抽出
    eval_df[["car1", "car2"]] = eval_df["pred_comb"].str.split("-", expand=True).astype(int)

    # レース単位で展開して選手単位に
    hit_rows = []
    for _, row in eval_df.iterrows():
        for car in [row["car1"], row["car2"]]:
            hit_rows.append({
                "date": row["date"],
                "venue_id": row["venue_id"],
                "race_no": row["race_no"],
                "car_no": car,
                "hit": row["hit"]
            })

    hit_df = pd.DataFrame(hit_rows)

    # 結果データとマージ
    merged = pd.merge(results_df, hit_df, how="left",
                      on=["date", "venue_id", "race_no", "car_no"])
    merged["hit"] = merged["hit"].fillna(0)

    # ベースとなる出力する特徴量列
    base_feature_cols = [
        "racer_id", "date", "car_no", "rank", "line_pos", "line_id",
        "grade", "venue_id", "prefecture", "race_no", "age", "hit"
    ]

    # オプションの列（存在すれば追加）
    optional_cols = ["area", "group"]
    feature_cols = base_feature_cols + [col for col in optional_cols if col in merged.columns]

    output_path = OUTPUT_PATH / f"step7_train_feedback_only_niren_{target_date}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged[feature_cols].to_csv(output_path, index=False)
    print(f"✅ フィードバック学習データを保存しました: {output_path}")

if __name__ == "__main__":
    main()