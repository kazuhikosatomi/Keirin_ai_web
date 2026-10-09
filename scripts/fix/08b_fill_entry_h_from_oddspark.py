#!/usr/bin/env python3

import argparse
from pathlib import Path
import pandas as pd


ENTRY_ROOT = Path("data/entries")
ODDSPARK_ROOT = Path("data/entries/oddspark")

KEYS = ["venue_id", "race_no", "car_no"]


def normalize_date(s):
    s = str(s).strip().replace("-", "")
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"invalid date: {s}")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def generate_dates(start, end):
    return [
        d.strftime("%Y-%m-%d")
        for d in pd.date_range(
            normalize_date(start),
            normalize_date(end),
            freq="D",
        )
    ]


def fill_one_date(date):
    year = date[:4]

    entry_path = ENTRY_ROOT / year / f"entry_{date}.csv"
    op_path = ODDSPARK_ROOT / year / f"entry_{date}.csv"

    if not entry_path.exists():
        raise FileNotFoundError(
            f"formal entry not found: {entry_path}"
        )

    if not op_path.exists():
        raise FileNotFoundError(
            f"OddsPark entry not found: {op_path}"
        )

    entry = pd.read_csv(entry_path, low_memory=False)
    op = pd.read_csv(op_path, low_memory=False)

    for c in KEYS:
        if c not in entry.columns:
            raise ValueError(
                f"{date}: formal entry key missing: {c}"
            )
        if c not in op.columns:
            raise ValueError(
                f"{date}: OddsPark key missing: {c}"
            )

        entry[c] = pd.to_numeric(
            entry[c],
            errors="coerce",
        )
        op[c] = pd.to_numeric(
            op[c],
            errors="coerce",
        )

    if "H" not in op.columns:
        raise ValueError(
            f"{date}: OddsPark H column missing"
        )

    if "H" not in entry.columns:
        entry["H"] = pd.NA

    entry["H"] = pd.to_numeric(
        entry["H"],
        errors="coerce",
    )

    op_h = op[KEYS + ["H"]].copy()
    op_h["H"] = pd.to_numeric(
        op_h["H"],
        errors="coerce",
    )

    dup = op_h.duplicated(KEYS, keep=False)

    if dup.any():
        raise ValueError(
            f"{date}: OddsPark duplicate keys="
            f"{int(dup.sum())}"
        )

    before_h = entry["H"].copy()

    merged = entry.merge(
        op_h.rename(columns={"H": "_oddspark_H"}),
        on=KEYS,
        how="left",
        validate="many_to_one",
    )

    missing_before = merged["H"].isna()
    fillable = (
        missing_before
        & merged["_oddspark_H"].notna()
    )
    unresolved = (
        missing_before
        & merged["_oddspark_H"].isna()
    )

    if unresolved.any():
        sample_cols = [
            c for c in [
                "date",
                "venue_id",
                "race_no",
                "car_no",
                "racer_name",
                "H",
                "_oddspark_H",
            ]
            if c in merged.columns
        ]

        print(
            merged.loc[
                unresolved,
                sample_cols,
            ].head(20).to_string(index=False)
        )

        raise ValueError(
            f"{date}: unresolved H="
            f"{int(unresolved.sum())}"
        )

    merged.loc[
        fillable,
        "H",
    ] = merged.loc[
        fillable,
        "_oddspark_H",
    ]

    merged = merged.drop(
        columns=["_oddspark_H"]
    )

    # 既存WINTICKET Hが1件も変わっていないことを確認。
    existing = before_h.notna()

    before_existing = (
        before_h.loc[existing]
        .reset_index(drop=True)
    )
    after_existing = (
        merged.loc[existing, "H"]
        .reset_index(drop=True)
    )

    if not before_existing.equals(after_existing):
        raise ValueError(
            f"{date}: existing WINTICKET H changed"
        )

    missing_after = int(
        merged["H"].isna().sum()
    )

    if missing_after:
        raise ValueError(
            f"{date}: H missing after fill="
            f"{missing_after}"
        )

    # H以外の列構成・行数を変えない。
    if len(merged) != len(entry):
        raise ValueError(
            f"{date}: row count changed "
            f"{len(entry)} -> {len(merged)}"
        )

    fill_count = int(fillable.sum())

    # 補完対象が0件なら正式entryを再保存しない。
    # CSV再保存だけでファイル内容が変化することを防ぐ。
    if fill_count == 0:
        print(
            f"[OK] {date} "
            f"rows={len(entry)} "
            f"H_missing_before=0 "
            f"H_filled=0 "
            f"H_missing_after=0 "
            f"saved=no"
        )
        return

    merged.to_csv(
        entry_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(
        f"[OK] {date} "
        f"rows={len(merged)} "
        f"H_missing_before={int(missing_before.sum())} "
        f"H_filled={fill_count} "
        f"H_missing_after={missing_after} "
        f"saved=yes"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "正式entryのH欠損だけを"
            "OddsPark Hで補完する"
        )
    )

    parser.add_argument("--date")
    parser.add_argument("--start")
    parser.add_argument("--end")

    args = parser.parse_args()

    if args.date:
        dates = [normalize_date(args.date)]
    elif args.start and args.end:
        dates = generate_dates(
            args.start,
            args.end,
        )
    else:
        raise ValueError(
            "--date または --start --end を指定してください"
        )

    print("=" * 60)
    print("START 08b_fill_entry_h_from_oddspark.py")
    print(
        "rule: existing H = keep / "
        "missing H = OddsPark fallback"
    )
    print("=" * 60)

    for date in dates:
        fill_one_date(date)

    print("=" * 60)
    print(
        f"OK: dates={len(dates)}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
