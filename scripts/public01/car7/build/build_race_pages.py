#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_race_pages.py

目的:
最新のオッズ結合CSVを読み込み、デザイン済みテンプレートへ
レース詳細データを差し込んで、競輪場別・レース別HTMLを生成する。

入力:
data/public01/car7/watch/public01_car7_tickets_with_odds_YYYY-MM-DD.csv
data/bet01/car7/step43/bet01_car7_step43_all_top_tickets_YYYY-MM-DD.csv

出力:
tmp/public01/car7/latest/snapshot/vXX/races/rYY.html

重要:
- r00_template.html はデザイン原本なので上書きしない
- --race-id 未指定時は、その日の全レースページを自動生成する
- レース移動ナビは同一 venue_id 内だけを表示する
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
from pathlib import Path
import re

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.public01.car7.common.constants import VENUE_NAME_MAP
from scripts.public01.car7.common.html_replace import replace_first_tbody_after_heading
from scripts.public01.car7.common.render_race_page import replace_basic_text
from scripts.public01.car7.common.ai_race import load_ai_race_meta
from scripts.public01.car7.common.utils import (
    normalize_race_no_value,
    build_line_pair_stats_html,
    build_lineup_html,
    build_event_title_from_meta,
    build_racer_stats_html,
    detect_column,
    find_entry_path,
    load_race_meta,
    normalize_time_text,
    parse_race_id,
)

from scripts.public01.car7.common.result import (
    build_ticket_rows,
    load_result_payouts,
)

from scripts.public01.car7.common.odds import (
    build_odds_popularity_html,
    calc_odds_status,
    load_real_odds_popularity_source,
    render_odds_badge,
)

from scripts.public01.car7.common.arare import (
    load_arare_meta,
    render_arare_badge,
)



DEFAULT_DATE = "2026-04-26"
DEFAULT_TEMPLATE_PATH = Path("docs/grade05/templates/r00_template.html")
DEFAULT_OUTPUT_PATH = Path("tmp/public01/car7/latest/snapshot/v00/races/r00.html")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--race-id", default=None, help="対象race_id。未指定ならCSV先頭のrace_id")
    parser.add_argument("--top-exacta", type=int, default=2, help="2車単の表示件数")
    parser.add_argument("--top-trifecta", type=int, default=5, help="3連単の表示件数")
    parser.add_argument("--top-trio", type=int, default=3, help="3連複の表示件数")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE_PATH), help="HTMLテンプレート")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="出力HTML")
    parser.add_argument("--verbose", action="store_true", help="詳細ログを表示する")
    return parser.parse_args()


def sort_races_by_number(df: pd.DataFrame) -> pd.DataFrame:
    """レース番号を文字列ではなく数値として昇順に並べる。"""
    out = df.copy()

    if "race_no" in out.columns:
        out["_race_no_num"] = pd.to_numeric(
            out["race_no"],
            errors="coerce",
        )
    elif "race_id" in out.columns:
        out["_race_no_num"] = pd.to_numeric(
            out["race_id"]
            .astype(str)
            .str.extract(
                r"(?:_r|_)(\d+)$",
                expand=False,
            ),
            errors="coerce",
        )
    else:
        out["_race_no_num"] = pd.NA

    out = out.dropna(
        subset=["_race_no_num"]
    )

    sort_cols = []

    if "venue_id" in out.columns:
        out["_venue_id_num"] = pd.to_numeric(
            out["venue_id"],
            errors="coerce",
        )
        sort_cols.append("_venue_id_num")

    sort_cols.append("_race_no_num")

    out = out.sort_values(
        sort_cols,
        kind="stable",
    )

    return out


def load_ticket_source(date: str) -> pd.DataFrame:
    """public01 car7ではbet01 car7 step43を最優先で読む。"""
    watch_path = Path(
        f"data/public01/car7/watch/"
        f"public01_car7_tickets_with_odds_{date}.csv"
    )
    step04_path = Path(
        f"data/public01/car7/step04/"
        f"public01_car7_tickets_with_odds_{date}.csv"
    )
    step43_path = Path(
        f"data/bet01/car7/step43/"
        f"bet01_car7_step43_all_top_tickets_{date}.csv"
    )

    # public01 car7 のレースページは、
    # bet01 Step43 に実オッズを結合した
    # watch/tickets_with_odds を最優先で使用する。
    #
    # 朝の初期段階など watch がまだ無い場合のみ
    # bet01 Step43 へフォールバックする。
    if watch_path.exists():
        path = watch_path
        source_name = "watch_with_odds"

    elif step43_path.exists():
        path = step43_path
        source_name = "bet01_car7_step43"

    elif step04_path.exists():
        path = step04_path
        source_name = "step04_with_odds"

    else:
        raise FileNotFoundError(
            "ticket source not found: "
            f"{step43_path}, {watch_path}, {step04_path}"
        )

    df = pd.read_csv(path)

    # sim08のrace_id:
    #   YYYY-MM-DD_v45_r1
    # public01 car7共通処理が期待する形式:
    #   YYYY-MM-DD_45_1
    if (
        source_name == "bet01_car7_step43"
        and "race_id" in df.columns
    ):
        df["race_id"] = (
            df["race_id"]
            .astype(str)
            .str.replace(
                r"_v(\d+)_r(\d+)$",
                r"_\1_\2",
                regex=True,
            )
        )

    print(
        f"📥 ticket source: "
        f"{source_name} -> {path}"
    )

    return sort_races_by_number(df)


# ==================== Race meta / navigation ====================


# レースページ内ナビ（同一開催のみ）
def build_numeric_race_list(df: pd.DataFrame) -> pd.DataFrame:
    """race_idを会場番号・レース番号の数値順に並べる。"""
    out = df.copy()

    if "race_id" not in out.columns:
        return out.iloc[0:0].copy()

    keep_cols = [
        col
        for col in [
            "race_id",
            "venue_id",
            "race_no",
        ]
        if col in out.columns
    ]

    out = (
        out[keep_cols]
        .drop_duplicates(
            subset=["race_id"],
            keep="first",
        )
        .copy()
    )

    if "venue_id" in out.columns:
        out["_venue_id_num"] = pd.to_numeric(
            out["venue_id"],
            errors="coerce",
        )
    else:
        out["_venue_id_num"] = pd.to_numeric(
            out["race_id"]
            .astype(str)
            .str.extract(
                r"(?:_v|_)(\d+)(?:_r|_)",
                expand=False,
            ),
            errors="coerce",
        )

    if "race_no" in out.columns:
        out["_race_no_num"] = pd.to_numeric(
            out["race_no"],
            errors="coerce",
        )
    else:
        out["_race_no_num"] = pd.to_numeric(
            out["race_id"]
            .astype(str)
            .str.extract(
                r"(?:_r|_)(\d+)$",
                expand=False,
            ),
            errors="coerce",
        )

    out = out.dropna(
        subset=[
            "_venue_id_num",
            "_race_no_num",
        ]
    )

    out = out.sort_values(
        [
            "_venue_id_num",
            "_race_no_num",
        ],
        ascending=True,
        kind="stable",
    )

    return out


def build_race_page_nav_html(date: str, current_race_id: str) -> str:
    """同一開催内の他レース詳細ページへ移動するためのリンクを生成する。"""
    step43_path = Path(f"data/bet01/car7/step43/bet01_car7_step43_all_top_tickets_{date}.csv")
    if not step43_path.exists():
        return ""

    try:
        nav_df = pd.read_csv(step43_path)
        nav_df = sort_races_by_number(nav_df)

        if "race_id" in nav_df.columns:
            nav_df["race_id"] = (
                nav_df["race_id"]
                .astype(str)
                .str.replace(
                    r"_v(\d+)_r(\d+)$",
                    r"_\1_\2",
                    regex=True,
                )
            )
    except Exception:
        return ""

    if nav_df.empty or "race_id" not in nav_df.columns:
        return ""

    try:
        _, current_venue_id, _ = parse_race_id(current_race_id)
    except Exception:
        return ""

    race_rows = build_numeric_race_list(nav_df)

    all_race_ids = (
        race_rows["race_id"]
        .astype(str)
        .tolist()
    )

    race_ids = []

    for rid in all_race_ids:
        try:
            _, venue_id, _ = parse_race_id(rid)
        except Exception:
            continue

        if int(venue_id) == int(current_venue_id):
            race_ids.append(rid)

    if not race_ids:
        return ""

    venue_name = VENUE_NAME_MAP.get(int(current_venue_id), f"v{int(current_venue_id)}")

    links = []
    for rid in race_ids:
        try:
            _, venue_id, race_no = parse_race_id(rid)
        except Exception:
            continue

        label = f"{race_no}R"
        href = f"./r{race_no:02d}.html"

        if rid == str(current_race_id):
            links.append(
                f'<span style="display:inline-block; padding:5px 9px; border-radius:999px; '
                f'background:#1d4ed8; color:#ffffff; font-weight:800; font-size:0.85rem; '
                f'margin:0 4px 6px 0;">{label}</span>'
            )
        else:
            links.append(
                f'<a href="{href}" style="display:inline-block; padding:5px 9px; border-radius:999px; '
                f'background:#eef2ff; color:#1d4ed8; font-weight:800; font-size:0.85rem; '
                f'text-decoration:none; margin:0 4px 6px 0;">{label}</a>'
            )

    if not links:
        return ""

    return f"""
  <div class="card" style="padding:12px 14px;">
    <div class="title" style="margin-bottom:8px;">レース移動（{html.escape(venue_name)}）</div>
    <div style="display:flex; flex-wrap:wrap; align-items:center;">
      {''.join(links)}
    </div>
  </div>
"""

def load_odds_watch_meta(date: str, race_id: str) -> tuple[str, str, str]:
    """
    watch用term_tableから実際のオッズ更新情報を取得する。

    戻り値:
      (odds_updated_at の HH:MM, odds_status, other_finalize_time)

    fetched_at や予定取得時刻は、
    実際のオッズ更新時刻としては使用しない。
    """
    candidates = [
        Path(f"data/public01/car7/watch/public01_car7_odds_term_table_{date}.csv"),
        Path(f"data/public01/car7/step05/public01_car7_odds_term_table_{date}.csv"),
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return "", "", ""

    df = pd.read_csv(path, dtype=str).fillna("")
    if "race_id" not in df.columns:
        return "", "", ""

    sub = df[df["race_id"].astype(str) == str(race_id)]
    if sub.empty:
        return "", "", ""

    row = sub.iloc[0]

    odds_status = str(
        row.get("odds_status", row.get("status", ""))
    ).lower().strip()

    other_finalize_time = str(
        row.get("other_finalize_time", "")
    ).strip()

    value = str(row.get("odds_updated_at", "")).strip()

    if not value:
        return "", odds_status, other_finalize_time

    dt = pd.to_datetime(value, errors="coerce")
    if pd.notna(dt):
        return dt.strftime("%H:%M"), odds_status, other_finalize_time

    return (
        normalize_time_text(value),
        odds_status,
        other_finalize_time,
    )



def load_single_arare_meta(date: str, race_id: str) -> dict:
    """レースページ用に荒れ度メタ情報を1レース分だけdictで取得する。"""
    try:
        _, venue_id, race_no = parse_race_id(race_id)
    except Exception:
        return {}

    arare_df = load_arare_meta(date)
    if arare_df.empty:
        return {}

    if not {"venue_id", "race_no"}.issubset(set(arare_df.columns)):
        return {}

    work = arare_df.copy()
    work["venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
    work["race_no"] = pd.to_numeric(work["race_no"], errors="coerce")

    sub = work[
        (work["venue_id"] == int(venue_id))
        & (work["race_no"] == int(race_no))
    ].copy()

    if sub.empty:
        return {}

    return sub.iloc[0].to_dict()


# ==================== Odds status / arare meta ====================

def load_racer_stats_table(date: str, race_id: str) -> pd.DataFrame:
    path = Path(f"data/bet01/car7/step12/bet01_car7_step12_first_predict_data_{date}.csv")
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()

    target_date, target_venue_id, target_race_no = parse_race_id(race_id)
    work = df.copy()

    # Normalize keys as much as possible.
    date_col = detect_column(work, ["date", "race_date"])
    venue_col = detect_column(work, ["venue_id", "place_id", "jyocode", "jyo_code"])
    race_col = detect_column(work, ["race_no", "race_num", "race_number", "race"])

    if date_col is not None:
        work["__date"] = pd.to_datetime(work[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
        work["__date"] = work["__date"].fillna(work[date_col].astype(str).str.slice(0, 10))
    else:
        work["__date"] = str(target_date)

    if venue_col is not None:
        work["__venue_id"] = pd.to_numeric(work[venue_col], errors="coerce")
    else:
        work["__venue_id"] = pd.NA

    if race_col is not None:
        work["__race_no"] = work[race_col].map(normalize_race_no_value)
    else:
        work["__race_no"] = pd.NA

    sub = work[
        (work["__date"].astype(str) == str(target_date))
        & (work["__venue_id"] == int(target_venue_id))
        & (work["__race_no"] == int(target_race_no))
    ].copy()
    if not sub.empty:
        return merge_ai_rider_rates(
            date,
            race_id,
            enrich_racer_stats_with_entry(date, race_id, sub),
        )

    # Fallback: normalize race_id if available.
    if "race_id" in work.columns:
        parsed_rows = []
        for rid in work["race_id"].astype(str):
            try:
                parsed_rows.append(parse_race_id(rid))
            except Exception:
                parsed_rows.append((None, None, None))
        work["__rid_date"] = [x[0] for x in parsed_rows]
        work["__rid_venue_id"] = [x[1] for x in parsed_rows]
        work["__rid_race_no"] = [x[2] for x in parsed_rows]
        sub = work[
            (work["__rid_date"].astype(str) == str(target_date))
            & (work["__rid_venue_id"] == int(target_venue_id))
            & (work["__rid_race_no"] == int(target_race_no))
        ].copy()
        if not sub.empty:
            return merge_ai_rider_rates(
            date,
            race_id,
            enrich_racer_stats_with_entry(date, race_id, sub),
        )

    return pd.DataFrame()


def merge_ai_rider_rates(date: str, race_id: str, stats_df: pd.DataFrame) -> pd.DataFrame:
    """Step35のAI1着率・AI3連対率を選手成績へ結合する。"""
    if stats_df.empty:
        return stats_df

    path = Path(
        f"data/bet01/car7/step35/"
        f"bet01_car7_step35_ai_rider_rates_{date}.csv"
    )
    if not path.exists():
        print(f"⚠️ Step35 AI rider rates not found: {path}")
        return stats_df

    ai = pd.read_csv(path)
    if ai.empty:
        return stats_df

    try:
        target_date, target_venue_id, target_race_no = parse_race_id(race_id)
    except Exception:
        print(f"⚠️ Step35 race_id parse failed: {race_id}")
        return stats_df

    ai["__date"] = pd.to_datetime(
        ai["date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    ai["__venue_id"] = pd.to_numeric(
        ai["venue_id"], errors="coerce"
    )
    ai["__race_no"] = pd.to_numeric(
        ai["race_no"], errors="coerce"
    )
    ai["car_no"] = pd.to_numeric(
        ai["car_no"], errors="coerce"
    )

    ai = ai[
        (ai["__date"].astype(str) == str(target_date))
        & (ai["__venue_id"] == int(target_venue_id))
        & (ai["__race_no"] == int(target_race_no))
    ].copy()

    if ai.empty:
        print(f"⚠️ Step35 target race not found: {race_id}")
        return stats_df

    keep = [
        "car_no",
        "ai_top1_pct",
        "ai_top1_rank",
        "ai_top3_pct",
        "ai_top3_rank",
    ]
    ai = ai[keep].copy()

    out = stats_df.copy()
    out["car_no"] = pd.to_numeric(
        out["car_no"], errors="coerce"
    )

    out = out.merge(
        ai,
        on="car_no",
        how="left",
        validate="one_to_one",
    )

    return out


def enrich_racer_stats_with_entry(date: str, race_id: str, stats_df: pd.DataFrame) -> pd.DataFrame:
    """step12に無い選手基本情報（班級・年齢・競走得点）をentryから補完する。"""
    if stats_df.empty:
        return stats_df

    # 並び予想はセリ情報を含む oddspark entry を優先する。
    # 通常entryはセリを別line_idへ分離しているため、
    # line_seri_order / line_is_seri を復元できない。
    year = str(date)[:4]
    oddspark_entry_path = Path(
        f"data/entries/oddspark/{year}/entry_{date}.csv"
    )

    if oddspark_entry_path.exists():
        entry_path = oddspark_entry_path
    else:
        entry_path = find_entry_path(date)

    if entry_path is None:
        return stats_df

    try:
        entry = pd.read_csv(entry_path)
    except Exception:
        return stats_df

    if entry.empty:
        return stats_df

    _, venue_id, race_no = parse_race_id(race_id)

    required_cols = {"venue_id", "race_no", "car_no"}
    if not required_cols.issubset(set(entry.columns)):
        return stats_df

    work = entry.copy()
    work["__venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
    work["__race_no"] = work["race_no"].map(normalize_race_no_value)
    work["__car_no"] = pd.to_numeric(work["car_no"], errors="coerce")

    work = work[
        (work["__venue_id"] == int(venue_id))
        & (work["__race_no"] == int(race_no))
        & (work["__car_no"].notna())
    ].copy()

    if work.empty:
        return stats_df

    # 選手基本情報に加えて、並び予想表示に必要な
    # ライン・セリ情報もentryから引き継ぐ。
    entry_cols = [
        "__car_no",
        "grade",
        "age",
        "score",
        "line_id",
        "line_pos",
        "line_is_seri",
        "line_seri_order",
        "line_has_seri",
    ]
    entry_cols = [c for c in entry_cols if c in work.columns]

    entry_small = work[
        entry_cols
    ].drop_duplicates(
        subset=["__car_no"],
        keep="last",
    ).rename(columns={
        "grade": "entry_racer_class",
        "age": "entry_racer_age",
        "score": "entry_racer_score",
    })

    # 通常entryから「本来のライン」を取得する。
    # OddsPark entry は競り込み後の配置、
    # 通常entryは競り前の元ラインとして両方を保持する。
    base_entry_path = Path(
        f"data/entries/{str(date)[:4]}/entry_{date}.csv"
    )

    base_line_small = None

    if base_entry_path.exists():
        try:
            base_entry = pd.read_csv(base_entry_path)

            if {"venue_id", "race_no", "car_no"}.issubset(base_entry.columns):
                base_entry["__venue_id"] = pd.to_numeric(
                    base_entry["venue_id"], errors="coerce"
                )
                base_entry["__race_no"] = base_entry["race_no"].map(
                    normalize_race_no_value
                )
                base_entry["__car_no"] = pd.to_numeric(
                    base_entry["car_no"], errors="coerce"
                )

                base_work = base_entry[
                    (base_entry["__venue_id"] == int(venue_id))
                    & (base_entry["__race_no"] == int(race_no))
                    & (base_entry["__car_no"].notna())
                ].copy()

                if (
                    not base_work.empty
                    and {"line_id", "line_pos"}.issubset(base_work.columns)
                ):
                    base_line_small = (
                        base_work[
                            ["__car_no", "line_id", "line_pos"]
                        ]
                        .drop_duplicates(
                            subset=["__car_no"],
                            keep="last",
                        )
                        .rename(columns={
                            "line_id": "base_line_id",
                            "line_pos": "base_line_pos",
                        })
                    )
        except Exception:
            base_line_small = None

    out = stats_df.copy()
    out["__car_no"] = pd.to_numeric(out.get("car_no"), errors="coerce")

    # 並び予想表示ではentryの生ライン情報を正とする。
    # step12にもline_id / line_posがあるため、そのままmergeすると
    # _x / _yになりbuild_lineup_html()から見えなくなる。
    entry_line_cols = [
        "line_id",
        "line_pos",
        "line_is_seri",
        "line_seri_order",
        "line_has_seri",
    ]
    out = out.drop(
        columns=[c for c in entry_line_cols if c in out.columns],
        errors="ignore",
    )

    out = out.merge(entry_small, on="__car_no", how="left")

    if base_line_small is not None:
        out = out.merge(
            base_line_small,
            on="__car_no",
            how="left",
        )

    out = out.drop(columns=["__car_no"], errors="ignore")

    return out





def print_event_summary_log(date: str, race_ids: list[str]) -> None:
    """全レース生成ログ用に開催名を1回だけ表示する。"""
    try:
        if not race_ids:
            return
        first_meta = load_race_meta(date, str(race_ids[0]))
        event_title = build_event_title_from_meta(first_meta)
        if event_title:
            print(f"📍 event: {event_title}")
    except Exception:
        return


def main():
    args = parse_args()
    date = args.date

    if args.race_id is None:
        df_all = load_ticket_source(date)
        race_ids = sorted(df_all["race_id"].astype(str).unique())

        print("=" * 72)
        print(f"🚀 START public01 car7 build all race pages | date={date}")
        print("=" * 72)
        print(f"📊 races: {len(race_ids)}")


        print_event_summary_log(args.date, race_ids)
        for rid in race_ids:
            try:
                _, venue_id, race_no = parse_race_id(rid)
            except Exception:
                print(f"⏭️ skip invalid race_id: {rid}")
                continue

            out_path = Path(
                f"tmp/public01/car7/latest/snapshot/"
                f"v{int(venue_id)}/races/r{int(race_no):02d}.html"
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                sys.executable,
                str(Path(__file__)),
                "--date", str(date),
                "--race-id", str(rid),
                "--output", str(out_path),
                "--template", str(args.template),
                "--top-exacta", str(args.top_exacta),
                "--top-trifecta", str(args.top_trifecta),
                "--top-trio", str(args.top_trio),
            ]
            subprocess.run(cmd, check=True)

        print("=" * 72)
        print(f"🎉 END public01 car7 build all race pages | date={date}")
        print("=" * 72)
        return
    template_path = Path(args.template)
    output_path = Path(args.output)

    if args.verbose:
        print(f"🚀 START public01 car7 build race pages generate sample race html | date={date}")

    if not template_path.exists():
        raise FileNotFoundError(template_path)

    df = load_ticket_source(date)
    race_id = args.race_id or str(df["race_id"].iloc[0])

    # race_idの表記差に依存せず、
    # date + venue_id + race_no で対象レースを特定する。
    target_date, target_venue_id, target_race_no = parse_race_id(race_id)

    parsed_rows = []
    for rid in df["race_id"].astype(str):
        try:
            parsed_rows.append(parse_race_id(rid))
        except Exception:
            parsed_rows.append((None, None, None))

    race_mask = [
        (
            str(rid_date) == str(target_date)
            and rid_venue_id == int(target_venue_id)
            and rid_race_no == int(target_race_no)
        )
        for rid_date, rid_venue_id, rid_race_no in parsed_rows
    ]

    race_df = df[race_mask].copy()

    if race_df.empty:
        raise ValueError(
            "race_id not found in step43 after normalized match: "
            f"{race_id}"
        )

    race_meta = load_race_meta(date, race_id)
    (
        odds_update_time,
        odds_watch_status,
        other_finalize_time,
    ) = load_odds_watch_meta(
        date,
        race_id,
    )
    arare_meta = load_single_arare_meta(date, race_id)
    ai_race_meta = load_ai_race_meta(
        date=date,
        venue_id=int(race_meta.get("venue_id", 0)),
        race_no=int(race_meta.get("race_no", 0)),
    )
    result_payouts = load_result_payouts(date, race_id)
    racer_df = load_racer_stats_table(date, race_id)
    racer_html = build_racer_stats_html(racer_df)
    line_pair_stats_html = build_line_pair_stats_html(date, race_id)
    lineup_html = build_lineup_html(racer_df, line_pair_stats_html=line_pair_stats_html)
    # race_id形式はcommon.utils.parse_race_id()で統一処理する。
    # legacy形式 / bet01形式のどちらもそのまま渡す。
    odds_popularity_df = load_real_odds_popularity_source(
        date,
        race_id,
    )
    if odds_popularity_df.empty:
        print("⚠️ real odds popularity source not found; fallback to AI ticket odds")
        odds_popularity_df = race_df
    odds_popularity_html = build_odds_popularity_html(odds_popularity_df)

    template = template_path.read_text(encoding="utf-8")
    rows_html = build_ticket_rows(
        race_df,
        top_exacta=args.top_exacta,
        top_trifecta=args.top_trifecta,
        top_trio=args.top_trio,
        result_payouts=result_payouts,
    )

    output_html = replace_basic_text(
        template,
        race_id,
        race_meta,
        odds_update_time,
        odds_watch_status,
        arare_meta,
        ai_race_meta,
        date,
        other_finalize_time,
    )
    race_page_nav_html = build_race_page_nav_html(date, race_id)
    if race_page_nav_html:
        nav_marker = '<div class="card">\n    <div class="title">レース情報</div>'
        if nav_marker in output_html:
            output_html = output_html.replace(nav_marker, race_page_nav_html + "\n" + nav_marker, 1)
    output_html = replace_first_tbody_after_heading(
        output_html,
        heading_text="AI予想（買い目）",
        tbody_html=rows_html,
    )
    stats_and_lineup_html = ""
    if racer_html:
        stats_and_lineup_html += racer_html + "\n"
    if lineup_html:
        stats_and_lineup_html += lineup_html + "\n"
    if odds_popularity_html:
        stats_and_lineup_html += odds_popularity_html + "\n"

    if stats_and_lineup_html:
        marker = '<div class="card">\n    <div class="title">AI予想（買い目）</div>'
        if marker in output_html:
            output_html = output_html.replace(marker, stats_and_lineup_html + marker, 1)
        else:
            output_html = output_html.replace("AI予想（買い目）", stats_and_lineup_html + "AI予想（買い目）", 1)

    venue_id_for_today = int(race_meta.get("venue_id", 0)) if isinstance(race_meta, dict) else 0
    if venue_id_for_today > 0:
        output_html = output_html.replace("../../today.html", "../index.html")
        output_html = output_html.replace("../today.html", "../index.html")

    # grade05共通テンプレート由来の表示文言をcar7専用に統一する。
    # 共通テンプレート本体はcar9/grade05でも使用するため変更しない。
    output_html = output_html.replace(
        "レース詳細 | グレードレース予想",
        "レース詳細 | 7車レース予想",
    )
    output_html = output_html.replace(
        "選手成績（グレードレース 過去1年）",
        "選手成績（7車レース 過去1年）",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_html, encoding="utf-8")

    if args.verbose:
        class_name_log = str(race_meta.get("class_name", "")).strip()
        class_name_part = f"（{class_name_log}）" if class_name_log else ""

        print(f"📄 template: {template_path}")
        print(f"📄 source: {df.attrs.get('source_path', 'unknown')}")
        print(f"📊 race_id: {race_id}")
        print(f"📊 event_title: {build_event_title_from_meta(race_meta)}")
        print(f"📊 page_title: 第{int(race_meta.get('race_no', 0))}レース{class_name_part}")
        print(f"📊 cup_name: {race_meta.get('cup_name', '') or '--'}")
        print(f"📊 cup_day: {race_meta.get('cup_day', '') or '--'}")
        print(f"📊 post_time: {race_meta.get('post_time', '') or '--'}")
        print(f"📊 odds_update_time: {odds_update_time or '--'}")
        print(f"📊 odds_status: {calc_odds_status(date, race_meta.get('post_time', ''), odds_update_time)}")
        print(f"📊 arare_index: {arare_meta.get('arare_index') if arare_meta.get('arare_index') is not None else '--'}")
        print(f"📊 racer_stats rows: {len(racer_df)}")
        print(f"📊 lineup: {'yes' if lineup_html else 'no'}")
        print(f"📊 odds_popularity: {'yes' if odds_popularity_html else 'no'}")
        print(f"📄 odds_popularity_source: {odds_popularity_df.attrs.get('source_path', 'ai_ticket_fallback') if not odds_popularity_df.empty else '--'}")
        print(f"📊 race_nav: {'yes' if race_page_nav_html else 'no'}")
        print(f"📊 result_payouts: {', '.join(result_payouts.keys()) if result_payouts else '--'}")
        print(f"📊 source rows: {len(race_df)}")
        print(f"📊 output top_exacta: {args.top_exacta}")
        print(f"📊 output top_trifecta: {args.top_trifecta}")
        print(f"📊 output top_trio: {args.top_trio}")
    if len(racer_df) == 0:
        print("⚠️ racer_stats not found for this race_id")
    print(f"💾 saved: {output_path}")
    if args.verbose:
        print(f"🎉 END public01 car7 build race pages generate sample race html | date={date}")


if __name__ == "__main__":
    main()
