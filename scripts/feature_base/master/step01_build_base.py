#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENTRY_DIR = PROJECT_ROOT / "data" / "entries"
ODDSPARK_ENTRY_DIR = PROJECT_ROOT / "data" / "entries" / "oddspark"
VENUE_MASTER_PATH = PROJECT_ROOT / "data" / "master" / "venue_master.csv"
OUT_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"


def find_entry_file(date: str) -> Path:
    year = date[:4]

    candidates = [
        # 正式主入力:
        # Chariloto + WINTICKET で作成した通常entryを優先する。
        ENTRY_DIR / year / f"entry_{date}.csv",

        # 旧entry互換
        ENTRY_DIR / f"entry_{date}.csv",

        # OddsParkは最終フォールバック。
        ODDSPARK_ENTRY_DIR / year / f"entry_{date}.csv",
    ]

    required_columns = {
        "date",
        "venue_id",
        "race_no",
        "car_no",
        "racer_id",
    }

    rejected = []

    for path in candidates:
        if not path.exists():
            rejected.append(
                f"{path}: file_not_found"
            )
            continue

        try:
            sample = pd.read_csv(
                path,
                nrows=1,
                low_memory=False,
            )
        except Exception as exc:
            rejected.append(
                f"{path}: read_error={exc}"
            )
            continue

        missing_columns = sorted(
            required_columns
            - set(sample.columns)
        )

        if missing_columns:
            rejected.append(
                f"{path}: missing_columns={missing_columns}"
            )
            continue

        if sample.empty:
            rejected.append(
                f"{path}: empty_file"
            )
            continue

        if rejected:
            print(
                "[INFO] entry fallback:"
            )

            for reason in rejected:
                print(
                    f"  skip -> {reason}"
                )

        print(
            f"[INFO] entry selected -> {path}"
        )

        return path

    raise FileNotFoundError(
        "usable entry file not found "
        f"for {date}:\n"
        + "\n".join(rejected)
    )



def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "racer_name": "racer_name",
        "name": "racer_name",
        "name_kanji": "racer_name",
        "race_num": "race_no",
        "race_number": "race_no",
        "venue": "venue_name",
        "place": "venue_name",
        "place_name": "venue_name",
        "keirinjo": "venue_name",
        "S": "s_mark",
        "B": "b_mark",
        "H": "h_mark",
        "score": "racer_score",
        "point": "racer_score",
        "競走得点": "racer_score",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def apply_core03_base_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Step01 base columns to core03 naming rules."""
    rename_map = {
        "grade": "profile_class_grade",
        "race_grade": "race_grade",
        "prefecture": "profile_prefecture",
        "area": "profile_area",
        "class_name": "profile_class_name",
        "age": "profile_age",
        "term": "profile_term",
        "s_mark": "entry_recent_s_count",
        "h_mark": "entry_recent_h_count",
        "b_mark": "entry_recent_b_count",
        "tactics": "racer_tactic_style",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def fill_venue_name_from_master(df: pd.DataFrame) -> pd.DataFrame:
    """Fill venue_name from venue_master using venue_id."""
    if "venue_id" not in df.columns:
        return df

    if not VENUE_MASTER_PATH.exists():
        return df

    venue_master = pd.read_csv(VENUE_MASTER_PATH)

    if not {"venue_id", "venue_name"}.issubset(venue_master.columns):
        return df

    venue_master = venue_master[["venue_id", "venue_name"]].drop_duplicates("venue_id")
    venue_master["venue_id"] = pd.to_numeric(
        venue_master["venue_id"], errors="coerce"
    ).astype("Int64")

    merged = df.merge(
        venue_master.rename(columns={"venue_name": "venue_name_master"}),
        on="venue_id",
        how="left",
        validate="many_to_one",
    )

    current = merged["venue_name"].astype("string").fillna("").str.strip()
    master = merged["venue_name_master"].astype("string").fillna("").str.strip()

    merged.loc[current.eq("") & master.ne(""), "venue_name"] = merged.loc[
        current.eq("") & master.ne(""), "venue_name_master"
    ]

    return merged.drop(columns=["venue_name_master"])


def fill_missing_entry_recent_from_history(
    df: pd.DataFrame,
    date: str,
) -> pd.DataFrame:
    """当日entryのS/H/B欠損を、D-1以前の最新有効entryから補完する。

    - racer_idのみで照合
    - 当日・未来日は参照しない
    - 現在値がある列は上書きしない
    """

    required = [
        "racer_id",
        "s_mark",
        "h_mark",
        "b_mark",
    ]

    if not set(required).issubset(df.columns):
        return df

    out = df.copy()

    for c in required:
        out[c] = pd.to_numeric(
            out[c],
            errors="coerce",
        )

    missing_mask = (
        out[
            [
                "s_mark",
                "h_mark",
                "b_mark",
            ]
        ]
        .isna()
        .any(axis=1)
    )

    if not missing_mask.any():
        return out

    target_date = pd.Timestamp(date)

    # 同じracer_idが複数行あっても検索は1回だけ。
    missing_racer_ids = (
        out.loc[
            missing_mask,
            "racer_id",
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    cache = {}

    for racer_id in missing_racer_ids:
        found = None

        # D-1以前を新しい順に探索。
        current = (
            target_date
            - pd.Timedelta(days=1)
        )

        # entry蓄積開始より十分前まで。
        lower_limit = pd.Timestamp("2024-01-01")

        while current >= lower_limit:
            date_str = current.strftime("%Y-%m-%d")
            year = date_str[:4]

            candidates = [
                # S/H/B の履歴補完は OddsPark を優先する。
                # 古い通常entryでは H 欠損・S/H/B列欠如があるため、
                # 通常entryはフォールバックとして使用する。
                ODDSPARK_ENTRY_DIR
                / year
                / f"entry_{date_str}.csv",

                ENTRY_DIR
                / year
                / f"entry_{date_str}.csv",
            ]

            for p in candidates:
                if not p.exists():
                    continue

                try:
                    hist = pd.read_csv(p)
                except Exception:
                    continue

                hist = normalize_columns(hist)

                needed = {
                    "racer_id",
                    "s_mark",
                    "h_mark",
                    "b_mark",
                }

                if not needed.issubset(hist.columns):
                    continue

                for c in needed:
                    hist[c] = pd.to_numeric(
                        hist[c],
                        errors="coerce",
                    )

                x = hist.loc[
                    hist["racer_id"].eq(
                        racer_id
                    )
                    & hist["s_mark"].notna()
                    & hist["h_mark"].notna()
                    & hist["b_mark"].notna()
                ]

                if x.empty:
                    continue

                row = x.iloc[-1]

                found = {
                    "date": date_str,
                    "s_mark": float(row["s_mark"]),
                    "h_mark": float(row["h_mark"]),
                    "b_mark": float(row["b_mark"]),
                }

                break

            if found is not None:
                break

            current -= pd.Timedelta(days=1)

        cache[racer_id] = found

        if found is None:
            print(
                "[WARN] entry_recent fallback not found "
                f"racer_id={racer_id}"
            )
        else:
            print(
                "[INFO] entry_recent fallback "
                f"racer_id={racer_id} "
                f"source={found['date']} "
                f"values="
                f"{found['s_mark']:g}/"
                f"{found['h_mark']:g}/"
                f"{found['b_mark']:g}"
            )

    # 欠けている列だけ補完
    for idx in out.index[missing_mask]:
        racer_id_value = out.at[
            idx,
            "racer_id",
        ]

        if pd.isna(racer_id_value):
            continue

        racer_id = int(
            racer_id_value
        )

        found = cache.get(
            racer_id
        )

        if found is None:
            continue

        for c in [
            "s_mark",
            "h_mark",
            "b_mark",
        ]:
            if pd.isna(
                out.at[idx, c]
            ):
                out.at[
                    idx,
                    c,
                ] = found[c]

    return out


def fill_missing_race_grade(
    date: str,
    out: pd.DataFrame,
) -> pd.DataFrame:
    """OddsPark entryでrace_gradeが欠損した場合のみ補完する。

    優先順:
    1. 通常entry
    2. results

    同日ファイル同士なので venue_id + race_no で照合する。
    """

    if "race_grade" not in out.columns:
        return out

    result = out.copy()

    missing_mask = (
        result["race_grade"].isna()
        | result["race_grade"].astype(str).str.strip().isin(
            ["", "nan", "None"]
        )
    )

    if not missing_mask.any():
        return result

    year = date[:4]

    for c in [
        "venue_id",
        "race_no",
    ]:
        result[c] = pd.to_numeric(
            result[c],
            errors="coerce",
        ).astype("Int64")

    def build_lookup(
        source_path: Path,
    ) -> pd.DataFrame | None:
        if not source_path.exists():
            return None

        src = pd.read_csv(
            source_path,
            low_memory=False,
        )

        src = normalize_columns(src)

        required = {
            "venue_id",
            "race_no",
            "race_grade",
        }

        if not required.issubset(
            src.columns
        ):
            return None

        src["venue_id"] = pd.to_numeric(
            src["venue_id"],
            errors="coerce",
        ).astype("Int64")

        src["race_no"] = pd.to_numeric(
            src["race_no"],
            errors="coerce",
        ).astype("Int64")

        src["race_grade"] = (
            src["race_grade"]
            .replace(
                ["", "nan", "None"],
                pd.NA,
            )
        )

        src = src.dropna(
            subset=[
                "venue_id",
                "race_no",
                "race_grade",
            ]
        ).copy()

        if src.empty:
            return None

        return (
            src[
                [
                    "venue_id",
                    "race_no",
                    "race_grade",
                ]
            ]
            .drop_duplicates(
                subset=[
                    "venue_id",
                    "race_no",
                ],
                keep="first",
            )
        )

    # ========================================================
    # 1. 通常entry
    # ========================================================
    normal_entry = (
        ENTRY_DIR
        / year
        / f"entry_{date}.csv"
    )

    lookup = build_lookup(
        normal_entry
    )

    if lookup is not None:
        before = int(
            result["race_grade"]
            .isna()
            .sum()
        )

        tmp = result.merge(
            lookup.rename(
                columns={
                    "race_grade":
                        "_fallback_race_grade"
                }
            ),
            on=[
                "venue_id",
                "race_no",
            ],
            how="left",
        )

        result["race_grade"] = (
            tmp["race_grade"]
            .fillna(
                tmp["_fallback_race_grade"]
            )
        )

        after = int(
            result["race_grade"]
            .isna()
            .sum()
        )

        filled = before - after

        if filled:
            print(
                "[INFO] race_grade fallback "
                f"entry filled: {filled}"
            )

    # ========================================================
    # 2. results
    # ========================================================
    still_missing = (
        result["race_grade"].isna()
    )

    if still_missing.any():
        results_path = (
            PROJECT_ROOT
            / "data"
            / "results"
            / year
            / f"results_{date}.csv"
        )

        lookup = build_lookup(
            results_path
        )

        if lookup is not None:
            before = int(
                result["race_grade"]
                .isna()
                .sum()
            )

            tmp = result.merge(
                lookup.rename(
                    columns={
                        "race_grade":
                            "_fallback_race_grade"
                    }
                ),
                on=[
                    "venue_id",
                    "race_no",
                ],
                how="left",
            )

            result["race_grade"] = (
                tmp["race_grade"]
                .fillna(
                    tmp["_fallback_race_grade"]
                )
            )

            after = int(
                result["race_grade"]
                .isna()
                .sum()
            )

            filled = before - after

            if filled:
                print(
                    "[INFO] race_grade fallback "
                    f"results filled: {filled}"
                )

    remaining = int(
        result["race_grade"]
        .isna()
        .sum()
    )

    if remaining:
        print(
            "[WARN] race_grade still "
            f"missing rows: {remaining}"
        )

    return result


def build_base(date: str) -> pd.DataFrame:
    entry_path = find_entry_file(date)
    df = pd.read_csv(entry_path)
    df = normalize_columns(df)

    required = ["date", "venue_id", "race_no", "car_no"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns in {entry_path}: {missing}")

    if "venue_name" not in df.columns:
        df["venue_name"] = ""

    keep_candidates = [
        "date",
        "venue_id",
        "venue_name",
        "race_no",
        "race_name",
        "cup_name",
        "cup_day",
        "post_time",
        "grade",
        "race_grade",
        "car_no",
        "racer_id",
        "racer_name",
        "prefecture",
        "area",
        "class_name",
        "grade_id",
        "age",
        "term",
        "racer_score",
        "line_id",
        "line_pos",
        "line_is_seri",
        "line_seri_order",
        "line_has_seri",
        "s_mark",
        "h_mark",
        "b_mark",
        "tactics",
    ]
    keep = [c for c in keep_candidates if c in df.columns]
    out = df[keep].copy()

    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["race_no"] = pd.to_numeric(out["race_no"], errors="coerce").astype("Int64")
    out["car_no"] = pd.to_numeric(out["car_no"], errors="coerce").astype("Int64")

    if "venue_id" in out.columns:
        out["venue_id"] = pd.to_numeric(out["venue_id"], errors="coerce").astype("Int64")
    if "line_id" in out.columns:
        out["line_id"] = pd.to_numeric(out["line_id"], errors="coerce").astype("Int64")
    if "line_pos" in out.columns:
        out["line_pos"] = pd.to_numeric(out["line_pos"], errors="coerce").astype("Int64")
    for col in ["line_is_seri", "line_seri_order", "line_has_seri"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")

    for col in ["s_mark", "h_mark", "b_mark", "age", "term", "racer_score"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out = fill_missing_entry_recent_from_history(
        out,
        date,
    )

    out = fill_missing_race_grade(
        date,
        out,
    )

    out = fill_venue_name_from_master(out)
    out = apply_core03_base_names(out)
    out = out.sort_values(["date", "venue_id", "race_no", "car_no"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("========== feature_base master / step01_base START ==========")
    print(f"[INFO] date={args.date}")
    out = build_base(args.date)
    latest_path = OUT_DIR / "step01_base_latest.csv"

    out.to_csv(latest_path, index=False)

    print(f"[OK] step01_base rows={len(out)} cols={len(out.columns)}")
    print(f"[OK] saved -> {latest_path}")
    print("========== feature_base master / step01_base END ==========")


if __name__ == "__main__":
    main()
