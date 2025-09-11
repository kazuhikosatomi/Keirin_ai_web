# -*- coding: utf-8 -*-
"""
Venue privacy ablation experiment.

1) Edit variables below, then run:
   python venue_privacy_experiment.py

Compares two settings:
  A) with_venue_id ........... uses venue_id (categorical)
  B) no_venue_id_binned ...... drops venue_id, uses ONLY binned physical features
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss, mean_squared_error
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import argparse, os

# ==== EDIT HERE ====
TRAIN_DATA_PATH = "data/9th/tmp/step2_train_data.csv"   # e.g., data/9th/tmp/step2_train_data.csv
VENUE_MASTER_PATH = "data/master/venue_master_with_bins.csv"
TARGET_COL = "YOUR_TARGET"                # e.g., is_arare
TASK_TYPE = "classification"              # 'classification' or 'regression'
MERGE_KEY = "venue_id"                    # join key (e.g., venue_id)
N_SPLITS = 5
RANDOM_STATE = 42
# ===================

def load_data(train_path: str, venue_path: str, merge_key: str):
    abs_train = os.path.abspath(train_path)
    abs_venue = os.path.abspath(venue_path)
    print(f"Loading train data from: {abs_train} (exists: {os.path.exists(abs_train)})")
    print(f"Loading venue master from: {abs_venue} (exists: {os.path.exists(abs_venue)})")
    train = pd.read_csv(train_path)
    venue = pd.read_csv(venue_path)
    if merge_key not in train.columns:
        raise KeyError(f"MERGE_KEY '{merge_key}' not found in TRAIN_DATA columns: {list(train.columns)}")
    if merge_key not in venue.columns:
        raise KeyError(f"MERGE_KEY '{merge_key}' not found in VENUE_MASTER columns: {list(venue.columns)}")
    return train.merge(venue, on=merge_key, how="left"), venue

def pick_binned_cols(df: pd.DataFrame):
    suffixes = ("_binned5", "_binned10", "_binned0p5")
    cols = [c for c in df.columns if c.endswith(suffixes)]
    if "straight_ratio_rounded2" in df.columns:
        cols.append("straight_ratio_rounded2")
    return cols

def prep_sets(df: pd.DataFrame, target_col: str, merge_key: str):
    if target_col not in df.columns:
        candidates = [c for c in ['is_arare','arare','label','y','target'] if c in df.columns]
        raise KeyError(f"TARGET_COL '{target_col}' not found in data columns. Candidate columns found: {candidates}")
    y = df[target_col]
    binned = pick_binned_cols(df)

    ignore = {target_col, merge_key}
    num_all = df.select_dtypes(include=[np.number]).drop(columns=[c for c in ignore if c in df.columns], errors="ignore")
    num_cols = list(num_all.columns)

    # A) with venue_id
    Xa = df[num_cols + [merge_key]].copy()
    # B) without venue_id, binned only
    Xb = df[binned].copy()
    if Xb.shape[1] == 0:
        print("⚠️  no binned physical feature columns detected; falling back to numeric features only (no venue_id)")
        Xb = df.select_dtypes(include=[np.number]).drop(columns=[c for c in {target_col, merge_key} if c in df.columns], errors="ignore").copy()
    return Xa, Xb, y

def _build_preprocessor(cat_cols):
    transformers = []
    if cat_cols:
        transformers.append(
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
        )
    # All other columns pass through; they should already be numeric per caller
    return ColumnTransformer(
        transformers=transformers,
        remainder="passthrough",
        verbose_feature_names_out=False,
    )

def build_classifier(cat_cols):
    pre = _build_preprocessor(cat_cols)
    model = RandomForestClassifier(
        n_estimators=300,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced",
    )
    # After preprocessing, impute any remaining NaN numerics
    return Pipeline([
        ("prep", pre),
        ("impute", SimpleImputer(strategy="median")),
        ("model", model),
    ])

def build_regressor(cat_cols):
    pre = _build_preprocessor(cat_cols)
    model = RandomForestRegressor(
        n_estimators=300,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline([
        ("prep", pre),
        ("impute", SimpleImputer(strategy="median")),
        ("model", model),
    ])

def cv_eval(X, y, model, task):
    try:
        skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE) if task=="classification" else None
    except Exception:
        skf = None

    if task=="classification" and skf is not None:
        splits = skf.split(X, y)
    else:
        kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
        splits = kf.split(X)

    metrics = []
    for tr, va in splits:
        Xtr, Xva = X.iloc[tr], X.iloc[va]
        ytr, yva = y.iloc[tr], y.iloc[va]
        model.fit(Xtr, ytr)
        if task=="classification":
            proba = getattr(model, "predict_proba", None)
            if proba is not None:
                p = model.predict_proba(Xva)[:,1]
                auc = roc_auc_score(yva, p)
                ll = log_loss(yva, p, labels=[0,1])
            else:
                auc = np.nan; ll = np.nan
            acc = accuracy_score(yva, model.predict(Xva))
            metrics.append({"auc":auc, "logloss":ll, "accuracy":acc})
        else:
            pred = model.predict(Xva)
            rmse = mean_squared_error(yva, pred, squared=False)
            metrics.append({"rmse":rmse})
    keys = sorted({k for d in metrics for k in d.keys()})
    avg = {k: np.nanmean([d.get(k, np.nan) for d in metrics]) for k in keys}
    return avg

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', default=TRAIN_DATA_PATH, help='Path to training CSV')
    parser.add_argument('--venue', default=VENUE_MASTER_PATH, help='Path to venue master with binned features')
    parser.add_argument('--target', default=TARGET_COL, help='Target column name')
    parser.add_argument('--task', default=TASK_TYPE, choices=['classification','regression'], help='Task type')
    parser.add_argument('--merge-key', dest='merge_key', default=MERGE_KEY, help='Join key (e.g., venue_id)')
    args = parser.parse_args()

    abs_train = os.path.abspath(args.train)
    abs_venue = os.path.abspath(args.venue)
    print(f"START: train={abs_train}, venue={abs_venue}, target={args.target}, task={args.task}, merge_key={args.merge_key}")

    if not os.path.exists(abs_train):
        print(f"Training data file does not exist: {abs_train}")
        return
    if not os.path.exists(abs_venue):
        print(f"Venue master file does not exist: {abs_venue}")
        return

    df, venue = load_data(args.train, args.venue, args.merge_key)

    # --- Drop rows with NaN target (cannot run CV with NaN labels)
    if args.target not in df.columns:
        raise KeyError(f"Target '{args.target}' not found after merge. Columns: {list(df.columns)[:30]} ...")
    before = len(df)
    nan_cnt = df[args.target].isna().sum()
    if nan_cnt > 0:
        print(f"⚠️  target '{args.target}' contains NaN: {nan_cnt} rows → dropping before CV")
        df = df.dropna(subset=[args.target]).reset_index(drop=True)
    print(f"📏 rows: before={before}, after_dropna={len(df)}")

    Xa, Xb, y = prep_sets(df, args.target, args.merge_key)

    # --- Ensure classification has both classes; otherwise switch to plain KFold in cv_eval
    if args.task == "classification":
        uniq = pd.Series(y).unique()
        if len(uniq) < 2:
            print(f"⚠️  target has a single class {uniq}. StratifiedKFold may fail; switching to plain KFold.")

    if args.task=="classification":
        ma = build_classifier([args.merge_key])   # with venue_id
        mb = build_classifier([])            # without venue_id, binned only
    else:
        ma = build_regressor([args.merge_key])
        mb = build_regressor([])

    avga = cv_eval(Xa, y, ma, args.task)
    avgb = cv_eval(Xb, y, mb, args.task)

    print("\n==== RESULT (with_venue_id) ====") 
    print(avga)
    print("==== RESULT (no_venue_id_binned) ====") 
    print(avgb)
    print("\nメモ:") 
    print("- with_venue_id が高すぎる→会場依存が強い/リークの可能性") 
    print("- no_venue_id_binned が実用的→丸め特徴で十分学習できる可能性") 
    print(f"\nEffective settings: target={args.target}, task={args.task}, merge_key={args.merge_key}")

if __name__ == "__main__":
    main()
