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

    # racer_idは識別子なので文字列として保持する。
    # 数値読込すると 015310 -> 15310.0 のように
    # 先頭0消失・小数化が起きるため禁止。
    entry = pd.read_csv(
        entry_path,
        dtype={"racer_id": "string"},
        low_memory=False,
    )
    op = pd.read_csv(
        op_path,
        dtype={"racer_id": "string"},
        low_memory=False,
    )

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

    for col in ["S", "H", "B"]:
        if col not in op.columns:
            raise ValueError(
                f"{date}: OddsPark {col} column missing"
            )

    if "racer_id" not in op.columns:
        raise ValueError(
            f"{date}: OddsPark racer_id column missing"
        )

    for col in ["S", "H", "B"]:
        if col not in entry.columns:
            entry[col] = pd.NA

        entry[col] = pd.to_numeric(
            entry[col],
            errors="coerce",
        )

    if "racer_id" not in entry.columns:
        entry["racer_id"] = ""

    entry["racer_id"] = (
        entry["racer_id"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace({"nan": "", "None": ""})
    )

    op_fallback = op[
        KEYS + ["S", "H", "B", "racer_id"]
    ].copy()

    for col in ["S", "H", "B"]:
        op_fallback[col] = pd.to_numeric(
            op_fallback[col],
            errors="coerce",
        )

    op_fallback["racer_id"] = (
        op_fallback["racer_id"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace({"nan": "", "None": ""})
    )

    dup = op_fallback.duplicated(
        KEYS,
        keep=False,
    )

    if dup.any():
        raise ValueError(
            f"{date}: OddsPark duplicate keys="
            f"{int(dup.sum())}"
        )

    before_s = entry["S"].copy()
    before_h = entry["H"].copy()
    before_b = entry["B"].copy()
    before_racer_id = entry["racer_id"].copy()

    merged = entry.merge(
        op_fallback.rename(
            columns={
                "S": "_oddspark_S",
                "H": "_oddspark_H",
                "B": "_oddspark_B",
                "racer_id": "_oddspark_racer_id",
            }
        ),
        on=KEYS,
        how="left",
        validate="many_to_one",
    )

    sb_stats = {}

    # S/BもHと同様、既存値は保持して欠損だけOddsParkで補完する。
    for col, before_col in [
        ("S", before_s),
        ("B", before_b),
    ]:
        missing_col = merged[col].isna()

        fillable_col = (
            missing_col
            & merged[f"_oddspark_{col}"].notna()
        )
        unresolved_col = (
            missing_col
            & merged[f"_oddspark_{col}"].isna()
        )

        if unresolved_col.any():
            raise ValueError(
                f"{date}: unresolved {col}="
                f"{int(unresolved_col.sum())}"
            )

        merged.loc[
            fillable_col,
            col,
        ] = merged.loc[
            fillable_col,
            f"_oddspark_{col}",
        ]

        # 既存値が変わっていないことを確認。
        existing_col = before_col.notna()
        if not (
            before_col.loc[existing_col]
            .reset_index(drop=True)
            .equals(
                merged.loc[existing_col, col]
                .reset_index(drop=True)
            )
        ):
            raise ValueError(
                f"{date}: existing {col} changed"
            )

        missing_after_col = int(
            merged[col].isna().sum()
        )
        if missing_after_col:
            raise ValueError(
                f"{date}: {col} missing after fill="
                f"{missing_after_col}"
            )

        sb_stats[col] = {
            "missing_before": int(missing_col.sum()),
            "filled": int(fillable_col.sum()),
            "missing_after": missing_after_col,
        }

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

    # racer_idは既存値を保持し、
    # 欠損している行だけOddsParkから補完する。
    racer_missing_before = (
        merged["racer_id"].eq("")
    )

    racer_fillable = (
        racer_missing_before
        & merged["_oddspark_racer_id"].ne("")
    )

    racer_unresolved = (
        racer_missing_before
        & merged["_oddspark_racer_id"].eq("")
    )

    if racer_unresolved.any():
        sample_cols = [
            c for c in [
                "date",
                "venue_id",
                "race_no",
                "car_no",
                "name_kanji",
                "racer_name",
                "racer_id",
                "_oddspark_racer_id",
            ]
            if c in merged.columns
        ]

        print(
            merged.loc[
                racer_unresolved,
                sample_cols,
            ].head(20).to_string(index=False)
        )

        raise ValueError(
            f"{date}: unresolved racer_id="
            f"{int(racer_unresolved.sum())}"
        )

    merged.loc[
        racer_fillable,
        "racer_id",
    ] = merged.loc[
        racer_fillable,
        "_oddspark_racer_id",
    ]

    racer_fill_count = int(
        racer_fillable.sum()
    )

    # 05等ですでに取得できていたracer_idは
    # OddsPark値で上書きしない。
    existing_racer = before_racer_id.ne("")

    before_existing_racer = (
        before_racer_id.loc[existing_racer]
        .reset_index(drop=True)
    )
    after_existing_racer = (
        merged.loc[
            existing_racer,
            "racer_id",
        ]
        .reset_index(drop=True)
    )

    if not before_existing_racer.equals(
        after_existing_racer
    ):
        raise ValueError(
            f"{date}: existing racer_id changed"
        )

    merged = merged.drop(
        columns=[
            "_oddspark_S",
            "_oddspark_H",
            "_oddspark_B",
            "_oddspark_racer_id",
        ]
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
    s_fill_count = sb_stats["S"]["filled"]
    b_fill_count = sb_stats["B"]["filled"]

    # 補完対象が0件なら正式entryを再保存しない。
    # CSV再保存だけでファイル内容が変化することを防ぐ。
    if (
        s_fill_count == 0
        and fill_count == 0
        and b_fill_count == 0
        and racer_fill_count == 0
    ):
        print(
            f"[OK] {date} "
            f"rows={len(entry)} "
            f"S_missing_before={sb_stats['S']['missing_before']} "
            f"S_filled={s_fill_count} "
            f"S_missing_after={sb_stats['S']['missing_after']} "
            f"H_missing_before={int(missing_before.sum())} "
            f"H_filled=0 "
            f"H_missing_after={missing_after} "
            f"B_missing_before={sb_stats['B']['missing_before']} "
            f"B_filled={b_fill_count} "
            f"B_missing_after={sb_stats['B']['missing_after']} "
            f"racer_id_missing_before="
            f"{int(racer_missing_before.sum())} "
            f"racer_id_filled=0 "
            f"racer_id_missing_after=0 "
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
        f"S_missing_before={sb_stats['S']['missing_before']} "
        f"S_filled={s_fill_count} "
        f"S_missing_after={sb_stats['S']['missing_after']} "
        f"H_missing_before={int(missing_before.sum())} "
        f"H_filled={fill_count} "
        f"H_missing_after={missing_after} "
        f"B_missing_before={sb_stats['B']['missing_before']} "
        f"B_filled={b_fill_count} "
        f"B_missing_after={sb_stats['B']['missing_after']} "
        f"racer_id_missing_before="
        f"{int(racer_missing_before.sum())} "
        f"racer_id_filled={racer_fill_count} "
        f"racer_id_missing_after=0 "
        f"saved=yes"
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "正式entryのS/H/B/racer_id欠損だけを"
            "OddsParkで補完する"
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
        "rule: existing S/H/B/racer_id = keep / "
        "missing = OddsPark fallback"
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
