import argparse
import pandas as pd
import pickle
from pathlib import Path

def load_model(model_path):
    with open(model_path, "rb") as f:
        return pickle.load(f)

def load_features(feather_path):
    return pd.read_feather(feather_path)

def load_entry(entry_path):
    return pd.read_csv(entry_path)

def predict_and_rank(model, X, entry_df):
    y_pred = model.predict_proba(X)
    
    # 各クラスの予測確率を元に「期待順位」を計算（順位の重み付き平均）
    rank_classes = model.classes_
    expected_rank = (y_pred * rank_classes).sum(axis=1)

    entry_df = entry_df.copy()
    entry_df["expected_rank"] = expected_rank

    # レースごとに順位ソート（昇順）して、予測順位を付番
    entry_df["predicted_rank"] = (
        entry_df.groupby("race_no")["expected_rank"]
        .rank(method="first", ascending=True)
        .astype(int)
    )

    return entry_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--features", required=True)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    model = load_model(args.model)
    X = load_features(args.features)
    entry = load_entry(args.entry)

    print("📊 予測実行中...")
    result_df = predict_and_rank(model, X, entry)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(args.output, index=False)
    print(f"✅ 予測結果保存完了: {args.output}")