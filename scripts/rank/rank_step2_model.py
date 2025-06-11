import argparse
import pandas as pd
import lightgbm as lgb
import pickle
from pathlib import Path

def load_results_for_training(end_date: str, db_path="db/keirin_data.duckdb"):
    import duckdb
    con = duckdb.connect(db_path)

    query = f"""
    SELECT *
    FROM results
    WHERE date < '{end_date}'
      AND rank ~ '^[1-9]$'  -- 順位1〜9のみ対象（失格等除外）
    """
    df = con.execute(query).fetchdf()
    con.close()
    return df

def prepare_features(df):
    df = df.dropna(subset=["racer_id"])
    df = df[df["rank"].apply(lambda x: str(x).isdigit())].copy()
    drop_cols = [
        "rank", "venue_id", "date", "race_no", "racer_id",
        "line_id", "line_pos", "venue_name", "name_kanji", "prefecture",
        "grade", "margin", "finish_tactics", "s_mark", "b_mark",
        "age", "last_time"
    ]
    X = df.drop(columns=[col for col in drop_cols if col in df.columns])
    y = df["rank"].astype(int)
    print("🧬 使用特徴量一覧:")
    print(list(X.columns))
    print("🧪 欠損のあるカラム:")
    print(X.isna().sum()[X.isna().sum() > 0])
    print("🧬 使用特徴量一覧:")
    print(list(X.columns))
    return X, y

def train_model(X, y):
    model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=10,
        random_state=42,
        n_estimators=100
    )
    try:
        model.fit(X, y)
    except Exception as e:
        print("❌ モデル学習中にエラー:", e)
        raise
    return model

def save_model(model, output_path):
    with open(output_path, "wb") as f:
        pickle.dump(model, f)
    print(f"✅ モデル保存完了: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--end-date", required=True, help="例: 2020-01-01 → この日より前のデータで学習")
    parser.add_argument("--output", default="models/rank_model.pkl", help="保存先パス")
    args = parser.parse_args()

    print(f"📦 {args.end_date} 以前の結果データを読み込み中...")
    df = load_results_for_training(args.end_date)
    print(f"📊 読み込んだ結果データ数: {len(df)} 行")

    print(f"🧮 特徴量を整形中...")
    X, y = prepare_features(df)
    print(f"📊 学習用データ: {X.shape[0]} 行 × {X.shape[1]} 列")
    print(f"🎯 正解データ（rank）: {y.shape[0]} 件")
    print(f"🎯 ランク分布: {y.value_counts().sort_index().to_dict()}")

    print("🎓 モデル学習開始...")
    model = train_model(X, y)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    save_model(model, args.output)

    from sklearn.metrics import accuracy_score
    import matplotlib.pyplot as plt

    # 正解率の確認
    y_pred = model.predict(X)
    acc = accuracy_score(y, y_pred)
    print(f"✅ 訓練データに対する正解率: {acc:.4f}")

    # 特徴量重要度の可視化
    lgb.plot_importance(model, max_num_features=20)
    plt.tight_layout()
    plt.show()