# scripts/9th/9th_exp_venue_ablation.py
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import roc_auc_score

SCRIPT_NAME = "9th_exp_venue_ablation.py"

def load_train_and_label(train_path, label_path):
    df = pd.read_csv(train_path)
    if "is_arare" not in df.columns:
        labels = pd.read_csv(label_path).rename(columns={"label": "is_arare"})
        df = df.merge(labels[["date", "venue_id", "race_no", "is_arare"]],
                      on=["date", "venue_id", "race_no"], how="left")
    return df

def time_split(df, target_date_str, valid_days=60):
    df["date"] = pd.to_datetime(df["date"])
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    valid_start = target_date - timedelta(days=valid_days)
    mask_valid = df["date"].dt.date >= valid_start
    train_df = df[~mask_valid].copy()
    valid_df = df[mask_valid].copy()
    return train_df, valid_df, valid_start

def prep_features(df, drop_cols_extra=None):
    # カテゴリ類
    categorical_cols = [c for c in ["grade","prefecture","area","group","venue_id","race_grade","race_grade_encoded"] if c in df.columns]
    for c in categorical_cols:
        df[c] = df[c].astype(str).astype("category").cat.codes

    # 目的変数と除去列
    base_drop = ["is_arare","date","rank"]
    if "hit" in df.columns:
        base_drop.append("hit")
    if drop_cols_extra:
        base_drop += drop_cols_extra

    X = df.drop(columns=[c for c in base_drop if c in df.columns])
    y = df["is_arare"].astype(int)
    # categorical_feature は存在するものだけ
    cat_in_X = [c for c in ["grade","prefecture","area","group","venue_id","race_grade","race_grade_encoded"] if c in X.columns]
    return X, y, cat_in_X

def train_eval(Xtr, ytr, Xva, yva, categorical_cols, seed=42):
    lgb_train = lgb.Dataset(Xtr, label=ytr, categorical_feature=categorical_cols or [])
    lgb_valid = lgb.Dataset(Xva, label=yva, categorical_feature=categorical_cols or [], reference=lgb_train)

    params = dict(objective="binary", metric="auc", verbosity=-1, seed=seed)
    model = lgb.train(params, lgb_train, num_boost_round=300,
                      valid_sets=[lgb_train, lgb_valid],
                      valid_names=["train","valid"],
                      callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=False)])
    pred = model.predict(Xva, num_iteration=model.best_iteration)
    auc = roc_auc_score(yva, pred)
    return model, auc

def main(target_date):
    print(f"🚀 [START] {SCRIPT_NAME} target_date={target_date}")

    TRAIN_FILE = Path("data/9th/tmp/step2_train_data.csv")
    LABEL_FILE = Path("data/arare/arare2_merged.csv")
    OUT_DIR = Path("data/9th/exp"); OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_train_and_label(TRAIN_FILE, LABEL_FILE)
    print(f"📦 load: rows={len(df)} cols={len(df.columns)}")

    # 欠損行除去（最低限）
    needed = ["is_arare","racer_id"]
    miss = [c for c in needed if c not in df.columns]
    if miss:
        raise KeyError(f"❌ 欠損カラム: {miss} が step2 出力に存在しません")
    df = df.dropna(subset=["is_arare"])

    # 時系列スプリット
    train_df, valid_df, vs = time_split(df, target_date, valid_days=60)
    print(f"🗂 split: train={len(train_df)} valid={len(valid_df)} (valid from {vs})")

    # ========== 1) venue_id を含む ==========
    Xtr_on, ytr_on, cats_on = prep_features(train_df.copy())
    Xva_on, yva_on, _ = prep_features(valid_df.copy())
    model_on, auc_on = train_eval(Xtr_on, ytr_on, Xva_on, yva_on, cats_on)

    imp_on = pd.DataFrame({"feature": Xtr_on.columns,
                           "importance": model_on.feature_importance()}) \
                .sort_values("importance", ascending=False)
    imp_on.to_csv(OUT_DIR / "venue_on_feature_importance.csv", index=False)

    # ========== 2) venue_id を除く（アブレーション） ==========
    drop_extra = ["venue_id"]  # 必要なら ["venue_id","area","group"] などに拡張
    Xtr_off, ytr_off, cats_off = prep_features(train_df.copy(), drop_cols_extra=drop_extra)
    Xva_off, yva_off, _ = prep_features(valid_df.copy(), drop_cols_extra=drop_extra)
    # categorical 指定からも venue_id を外す
    cats_off = [c for c in cats_off if c != "venue_id"]

    model_off, auc_off = train_eval(Xtr_off, ytr_off, Xva_off, yva_off, cats_off)

    imp_off = pd.DataFrame({"feature": Xtr_off.columns,
                            "importance": model_off.feature_importance()}) \
                .sort_values("importance", ascending=False)
    imp_off.to_csv(OUT_DIR / "venue_off_feature_importance.csv", index=False)

    # 結果ログ
    print("📊 AUC (valid last 60d)")
    print(f"   • WITH  venue_id: {auc_on:.4f}")
    print(f"   • WITHOUT venue_id: {auc_off:.4f}")
    print(f"   → Δ (on - off) = {auc_on - auc_off:+.4f}")

    # ついでにモデルも保存（任意）
    joblib.dump(model_on, OUT_DIR / "venue_on_model.pkl")
    joblib.dump(model_off, OUT_DIR / "venue_off_model.pkl")

    print(f"📤 saved: {OUT_DIR}/venue_on_feature_importance.csv")
    print(f"📤 saved: {OUT_DIR}/venue_off_feature_importance.csv")
    print(f"✅ [END] {SCRIPT_NAME}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="基準日 (YYYY-MM-DD)")
    args = ap.parse_args()
    main(args.date)