import pandas as pd
from pathlib import Path
import argparse

SCRIPT_NAME = "9th_step8_generate_final_prediction.py"

def main(target_date: str):
    # ---- START LOG ----
    print(f"🚀 [START] {SCRIPT_NAME} target_date={target_date}")

    # 入力（step5c の日付付きレース単位ファイル）
    input_path = Path(f"data/9th/step5c/step5c_predictions_ranked_{target_date}.csv")
    output_path = Path(f"data/9th/step8/final_prediction_arare_{target_date}.csv")

    if not input_path.exists():
        print(f"⚠️ 入力ファイルが見つかりません: {input_path}")
        print(f"🏁 [END] {SCRIPT_NAME} (no output)")
        return

    # 読み込み
    df = pd.read_csv(input_path)
    print(f"📊 読み込み件数: {len(df)} 行 from {input_path}")

    # スコア列の決定（優先順位: combined → mean → arare_score）
    score_col = None
    for c in ["arare_score_combined", "arare_score_mean", "arare_score"]:
        if c in df.columns:
            score_col = c
            break
    if score_col is None:
        raise KeyError("arare_score 系のカラムが見つかりません（arare_score_combined/arare_score_mean/arare_score のいずれかが必要）")

    # 出力用カラム作成
    df_out = df.copy()
    df_out = df_out.rename(columns={score_col: "arare_score"})

    # 閾値で is_arare を算出（従来と同様に 0.8 を使用）
    df_out["is_arare"] = (df_out["arare_score"] >= 0.8).astype(int)

    # venue_name を付与
    venue_master_path = Path("data/master/venue_master.csv")
    if venue_master_path.exists():
        venue_master = pd.read_csv(venue_master_path)
        df_out = df_out.merge(venue_master[["venue_id", "venue_name"]], on="venue_id", how="left")
    else:
        print("⚠️ venue_master.csv が見つかりません。venue_name は空のままになります。")

    # 出力項目（存在するものだけ採用）
    final_columns = [
        "date", "venue_id", "venue_name", "race_no",
        "arare_score", "is_arare"
    ]
    final_columns = [c for c in final_columns if c in df_out.columns]
    df_final = df_out[final_columns].copy()

    # 保存
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False, float_format="%.2f")

    print(f"💾 保存完了: {output_path}")
    print(f"✅ [END] {SCRIPT_NAME}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, required=True, help="対象日付（例: 2025-08-08）")
    args = parser.parse_args()
    main(args.date)