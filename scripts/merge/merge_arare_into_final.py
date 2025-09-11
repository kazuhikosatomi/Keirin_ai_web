import pandas as pd
from pathlib import Path
import argparse

SCRIPT_NAME = "3rd_merge_arare_into_final.py"

def main(target_date: str):
    print(f"🚀 [START] {SCRIPT_NAME} target_date={target_date}")

    # 入力
    final_path = Path(f"docs/predict/csv/3rd/final_prediction_niren_{target_date}.csv")
    step5a_path = Path(f"data/9th/step5a/step5a_predictions_racer_{target_date}.csv")
    output_path = Path(f"docs/predict/csv/3rd/final_prediction_niren_with_arare_{target_date}.csv")

    missing = [str(p) for p in [final_path, step5a_path] if not p.exists()]
    if missing:
        print("⚠️ 入力ファイルが見つかりません:")
        for m in missing:
            print(f"   - {m}")
        print(f"🏁 [END] {SCRIPT_NAME} (no output)")
        return

    final_df = pd.read_csv(final_path)
    step5a_df = pd.read_csv(step5a_path)

    print(f"📊 読込: final={len(final_df)} 行, step5a={len(step5a_df)} 行")

    # 必須列チェック
    for need_col, name in [(final_df, "final_prediction"), (step5a_df, "step5a")]:
        if "racer_id" not in need_col.columns:
            print(f"⚠️ {name} に 'racer_id' がありません。空列として処理します。")
            need_col["racer_id"] = None

    # 型合わせ（混在に強く）
    final_df["racer_id"] = pd.to_numeric(final_df["racer_id"], errors="coerce").astype("Int64")
    step5a_df["racer_id"] = pd.to_numeric(step5a_df["racer_id"], errors="coerce").astype("Int64")

    # step5a 側の重複があれば集約（同一 racer_id に複数行 → 最大スコアを採用）
    if "arare_score" not in step5a_df.columns:
        print("⚠️ step5a に 'arare_score' 列がありません。0 で埋めます。")
        step5a_df["arare_score"] = 0.0
    step5a_agg = step5a_df.groupby("racer_id", dropna=False)["arare_score"].max().reset_index()

    # マージ（要件どおり racer_id キー）
    merged = final_df.merge(step5a_agg, on="racer_id", how="left")

    # arare_score を小数点以下3桁でフォーマット（文字列化）
    if "arare_score" in merged.columns:
        merged["arare_score"] = merged["arare_score"].fillna(0.0).map(lambda x: f"{x:.3f}")

    # racer_id 列を削除
    if "racer_id" in merged.columns:
        merged = merged.drop(columns=["racer_id"])

    # 並びを軽く整える（arare_scoreは末尾寄せ）
    cols = list(merged.columns)
    if "arare_score" in cols:
        cols.remove("arare_score")
        cols.append("arare_score")
        merged = merged[cols]

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    print(f"💾 保存完了: {output_path}")
    print(f"🏁 [END] {SCRIPT_NAME}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="対象日付 (YYYY-MM-DD)")
    args = parser.parse_args()
    main(args.date)