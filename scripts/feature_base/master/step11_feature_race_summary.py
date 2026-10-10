#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"

INPUT_CANDIDATES = [
    WORK_DIR / "step01_base_latest.csv",
]

OUTPUT = WORK_DIR / "step11_feature_race_summary_latest.csv"

RACE_KEYS = [
    "date",
    "venue_id",
    "race_no",
]


def resolve_input() -> Path:
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path

    available = sorted(
        path.name
        for path in WORK_DIR.glob("step01*.csv")
    )

    raise FileNotFoundError(
        "step01出力が見つかりません。"
        f" candidates={[str(path) for path in INPUT_CANDIDATES]}"
        f" available={available}"
    )


def population_std(series: pd.Series) -> float:
    numeric = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if numeric.empty:
        return float("nan")

    return float(
        numeric.std(ddof=0)
    )


def build_race_summary(
    df: pd.DataFrame,
) -> pd.DataFrame:
    missing_keys = [
        column
        for column in RACE_KEYS
        if column not in df.columns
    ]

    if missing_keys:
        raise ValueError(
            "レース集計キーが不足しています: "
            f"{missing_keys}"
        )

    required_sources = [
        "profile_age",
        "racer_score",
    ]

    missing_sources = [
        column
        for column in required_sources
        if column not in df.columns
    ]

    if missing_sources:
        raise ValueError(
            "集計元列が不足しています: "
            f"{missing_sources}"
        )

    work = df.copy()

    work["profile_age"] = pd.to_numeric(
        work["profile_age"],
        errors="coerce",
    )

    work["racer_score"] = pd.to_numeric(
        work["racer_score"],
        errors="coerce",
    )

    grouped = (
        work.groupby(
            RACE_KEYS,
            dropna=False,
            sort=False,
        )
        .agg(
            race_age_mean=(
                "profile_age",
                "mean",
            ),
            race_age_std=(
                "profile_age",
                population_std,
            ),
            race_score_max=(
                "racer_score",
                "max",
            ),
            race_score_mean=(
                "racer_score",
                "mean",
            ),
            race_score_min=(
                "racer_score",
                "min",
            ),
            race_score_std=(
                "racer_score",
                population_std,
            ),
        )
        .reset_index()
    )

    grouped["race_score_range"] = (
        grouped["race_score_max"]
        - grouped["race_score_min"]
    )

    output_columns = [
        *RACE_KEYS,
        "race_age_mean",
        "race_age_std",
        "race_score_max",
        "race_score_mean",
        "race_score_min",
        "race_score_range",
        "race_score_std",
    ]

    return grouped[
        output_columns
    ].copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        required=True,
        help="YYYY-MM-DD",
    )
    args = parser.parse_args()

    input_path = resolve_input()

    print("=" * 80)
    print(
        "feature_base master / "
        "step11_feature_race_summary START"
    )
    print(f"date   : {args.date}")
    print(f"input  : {input_path}")
    print(f"output : {OUTPUT}")

    df = pd.read_csv(
        input_path,
        keep_default_na=False,
        low_memory=False,
    )

    if "date" in df.columns:
        target_date = str(args.date)

        date_mask = (
            df["date"]
            .astype(str)
            .str.strip()
            .eq(target_date)
        )

        if date_mask.any():
            df = df.loc[
                date_mask
            ].copy()

    summary = build_race_summary(df)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"saved -> {OUTPUT} "
        f"rows={len(summary):,} "
        f"cols={len(summary.columns):,}"
    )

    if not summary.empty:
        print()
        print(summary.head(10).to_string(index=False))

    print(
        "feature_base master / "
        "step11_feature_race_summary END"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
