#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
RESULTS_DIR = PROJECT_ROOT / "data" / "results"
OUT_DIR = WORK_DIR


def find_base_file(date: str) -> Path:
    p = WORK_DIR / "step01_base_latest.csv"
    if not p.exists():
        raise FileNotFoundError(f"base file not found: {p}")
    return p


def find_results_file(date: str) -> Path:
    year = date[:4]
    candidates = [
        RESULTS_DIR / year / f"results_{date}.csv",
        RESULTS_DIR / f"results_{date}.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"results file not found for {date}: {candidates}")


def normalize_results_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "race_num": "race_no",
        "race_number": "race_no",
        "car_number": "car_no",
        "rank": "result_rank",
        "result": "result_rank",
        "status": "result_status_raw",
        "result_status": "result_status_raw",
        "finish_tactics": "result_finish_tactic",
        "finish_tactic": "result_finish_tactic",
        "tactics": "result_finish_tactic",
        "margin": "result_margin",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def normalize_result_status(value: object) -> str:
    """Normalize non-finish result labels to project-wide abbreviations."""
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if not s:
        return ""

    mapping = {
        "落車": "LC",
        "落": "LC",
        "LC": "LC",
        "失格": "DS",
        "失": "DS",
        "DS": "DS",
        "棄権": "WD",
        "棄": "WD",
        "WD": "WD",
        "欠場": "NS",
        "欠": "NS",
        "NS": "NS",
        "失外": "DQ",
        "DQ": "DQ",
    }
    return mapping.get(s, s)


def build_step02(date: str) -> pd.DataFrame:
    base = pd.read_csv(find_base_file(date))
    results = pd.read_csv(find_results_file(date))
    results = normalize_results_columns(results)

    required = ["date", "venue_id", "race_no", "car_no"]
    missing = [c for c in required if c not in results.columns]
    if missing:
        raise ValueError(f"missing required columns in results: {missing}")

    result_keep = [
        "date",
        "venue_id",
        "race_no",
        "car_no",
        "racer_id",
        "result_rank",
        "result_status_raw",
        "result_finish_tactic",
        "result_margin",
    ]
    result_keep = [c for c in result_keep if c in results.columns]
    results = results[result_keep].copy()

    for df in [base, results]:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["venue_id"] = pd.to_numeric(df["venue_id"], errors="coerce").astype("Int64")
        df["race_no"] = pd.to_numeric(df["race_no"], errors="coerce").astype("Int64")
        df["car_no"] = pd.to_numeric(df["car_no"], errors="coerce").astype("Int64")
        if "racer_id" in df.columns:
            df["racer_id"] = pd.to_numeric(df["racer_id"], errors="coerce").astype("Int64")

    key4 = ["date", "venue_id", "race_no", "car_no"]
    key5 = ["date", "venue_id", "race_no", "car_no", "racer_id"]
    result_value_cols = [
        c for c in ["result_rank", "result_status_raw", "result_finish_tactic", "result_margin"]
        if c in results.columns
    ]

    # resultsにracer_idがある場合は、まず5キーで安全に照合する。
    # 引退選手・新規選手・外国人などでracer_idが欠損する行は、4キーが一意な場合だけ後段で補完する。
    if "racer_id" in results.columns:
        results_with_id = results[results["racer_id"].notna()].copy()
        results_without_id = results[results["racer_id"].isna()].copy()

        dup5 = results_with_id[results_with_id.duplicated(key5, keep=False)]
        if len(dup5):
            sample = dup5[key5].head(20).to_dict("records")
            raise ValueError(f"results has duplicated key5 rows: {sample}")

        out = base.merge(
            results_with_id[key5 + result_value_cols],
            on=key5,
            how="left",
            validate="one_to_one",
        )

        if len(results_without_id):
            dup4 = results_without_id[results_without_id.duplicated(key4, keep=False)]
            if len(dup4):
                sample = dup4[key4].head(20).to_dict("records")
                raise ValueError(f"results has ambiguous racer_id-missing key4 rows: {sample}")

            fallback = results_without_id[key4 + result_value_cols].copy()
            fallback = fallback.rename(columns={c: f"{c}_fallback" for c in result_value_cols})
            out = out.merge(fallback, on=key4, how="left", validate="one_to_one")

            for c in result_value_cols:
                fb = f"{c}_fallback"
                if fb in out.columns:
                    out[c] = out[c].combine_first(out[fb])
                    out = out.drop(columns=[fb])
    else:
        dup4 = results[results.duplicated(key4, keep=False)]
        if len(dup4):
            sample = dup4[key4].head(20).to_dict("records")
            raise ValueError(f"results has duplicated key4 rows and no racer_id column: {sample}")

        out = base.merge(
            results[key4 + result_value_cols],
            on=key4,
            how="left",
            validate="one_to_one",
        )

    if "result_status_raw" not in out.columns:
        out["result_status_raw"] = ""

    out["result_status"] = out["result_status_raw"].apply(normalize_result_status)

    if "result_rank" in out.columns:
        rank_numeric = pd.to_numeric(out["result_rank"], errors="coerce")
        rank_text = out["result_rank"].astype("string").fillna("").str.strip()
        missing_status = out["result_status"].eq("") & rank_numeric.isna()
        out.loc[missing_status, "result_status"] = rank_text[missing_status].apply(normalize_result_status)
        out["result_rank"] = rank_numeric.astype("Int64")

    out.loc[out["result_status"].eq("") & out["result_rank"].notna(), "result_status"] = "OK"
    out.loc[out["result_status"].eq("") & out["result_rank"].isna(), "result_status"] = "UNKNOWN"

    out["result_label"] = ""

    rank_mask = out["result_rank"].notna()
    out.loc[rank_mask, "result_label"] = (
        out.loc[rank_mask, "result_rank"]
        .astype("Int64")
        .astype(str)
    )

    status_mask = out["result_status"].ne("OK")
    out.loc[status_mask, "result_label"] = out.loc[status_mask, "result_status"]

    out = out.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("========== feature_base master / step02a_base_with_results START ==========")
    print(f"[INFO] date={args.date}")

    out = build_step02(args.date)
    latest_path = OUT_DIR / "step02a_base_with_results_latest.csv"

    out.to_csv(latest_path, index=False)

    result_rank_non_null = out["result_rank"].notna().sum() if "result_rank" in out.columns else 0
    status_counts = out["result_status"].value_counts(dropna=False).to_dict() if "result_status" in out.columns else {}

    print(f"[OK] step02a_base_with_results rows={len(out)} cols={len(out.columns)}")
    print(f"[INFO] result_rank_non_null={result_rank_non_null}")
    print(f"[INFO] result_status_counts={status_counts}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step02a_base_with_results END ==========")


if __name__ == "__main__":
    main()
