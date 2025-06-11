import argparse
import pandas as pd
import pickle
from pathlib import Path

def load_model(model_path):
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    return model

def generate_predict_features(entry_path, model, output_path):
    df = pd.read_csv(entry_path)

    # 特徴量だけ抽出（モデルで学習された順序を使う）
    model_features = model.feature_name_
    X = df[model_features].copy()

    # データ型をfloat32に揃えておく（念のため）
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce").astype("float32")

    # 欠損があれば警告
    if X.isna().sum().sum() > 0:
        print("⚠️ 欠損値が存在します。後続処理に注意してください。")
        print(X.isna().sum())

    # Feather形式で保存
    X.reset_index(drop=True).to_feather(output_path)
    print(f"✅ 特徴量保存完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", required=True, help="entry_like_YYYY-MM-DD.csv のパス")
    parser.add_argument("--model", required=True, help="使用するモデルの .pkl パス")
    parser.add_argument("--output", required=True, help="出力先 .feather ファイルパス")
    args = parser.parse_args()

    model = load_model(args.model)
    generate_predict_features(args.entry, model, args.output)