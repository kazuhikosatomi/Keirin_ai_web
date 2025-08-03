import argparse
import pandas as pd
import lightgbm as lgb
import pickle
import os

def predict_arare(date_str):
    # 入力ファイルパス
    entry_file = f"data/9th/tmp/step4_make_entry.csv"
    model_file = f"data/9th/tmp/step3_arare_model.pkl"
    output_file = "data/9th/tmp/step5_predictions_racer.csv"

    if not os.path.exists(entry_file):
        print(f"❌ Entryファイルが見つかりません: {entry_file}")
        return

    if not os.path.exists(model_file):
        print(f"❌ モデルファイルが見つかりません: {model_file}")
        return

    # Entryデータ読み込み
    df = pd.read_csv(entry_file)
    # date カラムの調整（例: date_x に置き換わっている場合）
    if "date" not in df.columns:
        if "date_x" in df.columns:
            print("🔁 'date_x' を 'date' にリネームします。")
            df["date"] = df["date_x"]
        else:
            print("❌ 'date' カラムが見つかりません。")
            return
    df = df[df["date"] == date_str]  # 指定日のみを抽出

    if df.empty:
        print(f"⚠️ 指定日のデータが見つかりません: {date_str}")
        return

    # モデル読み込み
    with open(model_file, "rb") as f:
        model = pickle.load(f)

    # モデルが学習時に使っていた特徴量だけを取得
    feature_names = model.feature_name()
    X = df[feature_names].copy()

    # object型（文字列）の特徴量を数値化（Label Encoding）
    for col in X.select_dtypes(include=['object']).columns:
        X[col] = X[col].astype("category").cat.codes

    X = X.fillna(0)

    # 予測スコアの付与
    df["arare_score"] = model.predict(X)



    # 出力：必要カラムのみ保存
    output_cols = ["date", "venue_id", "race_no", "car_no", "racer_id", "rank", "arare_score"]
    output_cols = [col for col in output_cols if col in df.columns]
    df[output_cols].to_csv(output_file, index=False)
    print(f"📤 上書き保存: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="予測対象日 (YYYY-MM-DD)")
    args = parser.parse_args()

    predict_arare(args.date)