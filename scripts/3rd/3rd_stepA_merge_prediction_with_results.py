import pandas as pd
from datetime import datetime, timedelta
import os

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='基準日 (YYYY-MM-DD)', required=False)
    args = parser.parse_args()
    base_date = datetime.strptime(args.date, "%Y-%m-%d") if args.date else datetime.today()
    target_date = base_date

    # 📅 対象日付を「基準日」に設定
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"📅 処理対象日: {date_str}")

    # 📁 ファイルパス定義
    pred_path = f"docs/predict/csv/3rd/final_prediction_niren_{date_str}.csv"
    result_path = f"data/results/2025/results_{date_str}.csv"
    output_path = f"docs/results/csv/3rd/prediction_with_result_{date_str}.csv"

    # ✅ ファイル存在チェック
    if not os.path.exists(pred_path):
        print(f"❌ 予測ファイルが存在しません: {pred_path}")
        return
    if not os.path.exists(result_path):
        print(f"❌ 結果ファイルが存在しません: {result_path}")
        return

    # 📥 読み込み
    df_pred = pd.read_csv(pred_path)
    df_result = pd.read_csv(result_path)

    # 🧹 必要なカラムだけ抽出（rankを含める）
    df_result = df_result[["date", "venue_id", "race_grade", "race_no", "car_no", "rank"]]

    # 🔗 マージ処理
    df_merged = pd.merge(df_pred.drop(columns=["race_grade"], errors="ignore"), df_result, on=["date", "venue_id", "race_no", "car_no"], how="left")
    # race_gradeをrace_noの前に移動
    if "race_grade" in df_merged.columns:
        cols = list(df_merged.columns)
        if "race_no" in cols and "race_grade" in cols:
            cols.remove("race_grade")
            race_no_index = cols.index("race_no")
            cols.insert(race_no_index, "race_grade")
            df_merged = df_merged[cols]

    # 💾 保存
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_merged.to_csv(output_path, index=False)
    print(f"✅ マージ結果を保存しました: {output_path}")

if __name__ == "__main__":
    main()