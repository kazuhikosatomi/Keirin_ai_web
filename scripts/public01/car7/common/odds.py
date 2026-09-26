#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
common_odds.py

grade05 共通のオッズ更新メタ情報ユーティリティ。
"""

from __future__ import annotations

from pathlib import Path
import html
import re

import pandas as pd

from scripts.public01.car7.common.utils import (
    detect_column,
    normalize_race_no_value,
    parse_race_id,
    safe_text,
)

from scripts.public01.car7.common.utils import detect_column, normalize_time_text


def find_odds_term_path(date: str) -> Path | None:
    candidates = [
        Path(f"data/public01/car7/watch/public01_car7_odds_term_table_{date}.csv"),
        Path(f"data/public01/car7/step05/public01_car7_odds_term_table_{date}.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def empty_odds_meta() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "venue_id", "race_no", "odds_update_time"])


def load_odds_meta(date: str) -> pd.DataFrame:
    path = find_odds_term_path(date)
    if path is None:
        return empty_odds_meta()

    df = pd.read_csv(path)
    if df.empty:
        return empty_odds_meta()

    race_id_col = detect_column(df, ["race_id"])
    date_col = detect_column(df, ["date", "race_date"])
    venue_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code"])
    race_col = detect_column(df, ["race_no", "race_num", "race_number", "race"])
    time_col = detect_column(
        df,
        ["odds_updated_at", "fetched_at", "odds_update_time", "updated_at", "scraped_at"],
    )
    fallback_time_col = detect_column(df, ["odds_fetch_time"])
    # オッズ表示では odds_status を正本とする。
    # status は結果処理を含む全体状態なのでフォールバック扱い。
    status_col = detect_column(df, ["odds_status", "status"])

    if time_col is None and fallback_time_col is None:
        return empty_odds_meta()

    work = df.copy()

    if race_id_col is not None:
        parsed = work[race_id_col].astype(str).map(parse_race_id)
        work["date"] = parsed.map(lambda x: x[0])
        work["venue_id"] = parsed.map(lambda x: x[1])
        work["race_no"] = parsed.map(lambda x: x[2])
    elif venue_col is not None and race_col is not None:
        if date_col:
            work["date"] = work[date_col].astype(str)
        else:
            work["date"] = date
        work["venue_id"] = work[venue_col]
        work["race_no"] = work[race_col]
    else:
        return empty_odds_meta()

    work["date"] = work["date"].astype(str)
    work = work[work["date"] == date].copy()
    work["venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
    work["race_no"] = pd.to_numeric(work["race_no"], errors="coerce")

    if time_col is not None:
        work["odds_update_time"] = work[time_col].astype(str).replace({"nan": "", "NaT": "", "None": ""})
        work["odds_update_time"] = work["odds_update_time"].str.strip()
    else:
        work["odds_update_time"] = ""

    # fetched_at が無い古いterm_tableでは、status=doneの行だけ予定取得時刻を代替表示に使う
    if fallback_time_col is not None:
        fallback_values = work[fallback_time_col].astype(str).replace({"nan": "", "NaT": "", "None": ""}).str.strip()
        if status_col is not None:
            status_values = work[status_col].astype(str).str.lower().str.strip()
            done_mask = status_values.isin(["done", "odds_done", "completed", "complete", "success"])
        else:
            done_mask = work["odds_update_time"].astype(str).str.strip() != ""
        empty_mask = work["odds_update_time"].astype(str).str.strip() == ""
        work.loc[empty_mask & done_mask, "odds_update_time"] = fallback_values[empty_mask & done_mask]

    work = work.dropna(subset=["venue_id", "race_no"])

    if work.empty:
        return empty_odds_meta()

    work["venue_id"] = work["venue_id"].astype(int)
    work["race_no"] = work["race_no"].astype(int)

    # odds_update_time が空でも行を落とさない。
    # term table の odds_status は全Rの実処理状態なので、
    # 更新時刻とは独立して保持する。
    #
    # OTHER最終処理では odds_status=done でも
    # odds_fetch_time が空のRがあるため、ここで除外すると
    # 2R以降が pending 扱いへ戻ってしまう。
    # watch term table の odds_status を一覧表示の正本として残す。
    # pending            -> オッズ更新前
    # watching / running -> オッズ更新中
    # done               -> オッズ確定
    work["odds_status"] = (
        df.loc[work.index, status_col].astype(str).str.strip().str.lower()
        if status_col
        else ""
    )

    # OTHER開催の最終処理完了時刻。
    # 列がまだ無い日・未完了会場は空文字として扱う。
    if "other_finalize_time" in df.columns:
        work["other_finalize_time"] = (
            df.loc[work.index, "other_finalize_time"]
            .astype(str)
            .replace({"nan": "", "NaT": "", "None": ""})
            .str.strip()
        )
    else:
        work["other_finalize_time"] = ""

    return work[
        [
            "date",
            "venue_id",
            "race_no",
            "odds_update_time",
            "odds_status",
            "other_finalize_time",
        ]
    ].drop_duplicates(
        subset=["date", "venue_id", "race_no"],
        keep="last",
    )


def calc_odds_status(
    date: str,
    post_time: str,
    odds_update_time: str,
    term_odds_status: str = "",
) -> str:
    """オッズ取得状態を表示用に判定する。

    term table の odds_status がある場合は実処理状態を正本とする。
    """
    term_status = str(term_odds_status or "").strip().lower()

    if term_status == "done":
        return "オッズ確定"
    if term_status in {"watching", "running"}:
        return "オッズ更新中"
    if term_status == "pending":
        return "オッズ更新前"

    post_time_text = normalize_time_text(post_time)
    now_dt = pd.Timestamp.now()

    # 発走時刻が不明な場合
    if not post_time_text:
        return "オッズ更新中"

    post_dt = pd.to_datetime(f"{date} {post_time_text}", errors="coerce")

    if pd.isna(post_dt):
        return "オッズ更新中"

    odds_update_time_text = str(odds_update_time or "").strip()

    # 発走前でまだオッズ取得されていない場合は「更新前」
    if now_dt < post_dt and not odds_update_time_text:
        return "オッズ更新前"

    # 発走前でオッズ取得済みなら、まだ変動中なので「更新中」
    if now_dt < post_dt and odds_update_time_text:
        return "オッズ更新中"

    # 発走後でまだオッズ取得されていない場合も「更新中」
    if not odds_update_time_text:
        return "オッズ更新中"

    # 発走後に取得済みなら確定
    return "オッズ確定"


def render_odds_badge(odds_status: str) -> str:
    # 状態名の後ろに更新時刻が付いていても同じ色を使う。
    if odds_status.startswith("オッズ確定"):
        style = "background:#dcfce7; color:#166534;"
    elif odds_status.startswith("オッズ更新中"):
        style = "background:#dbeafe; color:#1e40af;"
    elif (
        odds_status.startswith("オッズ未取得")
        or odds_status.startswith("オッズ更新前")
    ):
        style = "background:#f3f4f6; color:#6b7280;"
    else:
        style = "background:#e5e7eb; color:#374151;"
    return f'<span class="badge waiting" style="{style}">{odds_status}</span>'


# 最新オッズ更新時刻
def latest_update_text(odds_meta: pd.DataFrame) -> str:
    if odds_meta.empty or "odds_update_time" not in odds_meta.columns:
        return "--:--"

    values = odds_meta["odds_update_time"].dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return "--:--"

    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.notna().any():
        return parsed.max().strftime("%H:%M")

    # fallback for plain HH:MM strings
    normalized = values.map(normalize_time_text)
    normalized = normalized[normalized != ""]
    if normalized.empty:
        return "--:--"
    return sorted(normalized)[-1]

# ==================== Odds popularity ====================
def find_real_odds_paths(date: str) -> list[Path]:
    year = str(date)[:4]
    candidates = [
        Path(f"data/public01/car7/step07/public01_car7_odds_{date}.csv"),
        Path(f"data/public01/car7/step07/public01_car7_odds_for_race_{date}.csv"),
        Path(f"data/public01/car7/step07/odds_{date}.csv"),
        Path(f"data/public01/car7/odds/{year}/public01_car7_odds_{date}.csv"),
        Path(f"data/public01/car7/odds/public01_car7_odds_{date}.csv"),
        Path(f"data/odds/{year}/odds_{date}.csv"),
        Path(f"data/odds/odds_{date}.csv"),
    ]
    return [p for p in candidates if p.exists()]


def normalize_bet_type_for_popularity(value) -> str:
    text = safe_text(value)
    if not text:
        return ""
    text_upper = text.upper()

    # 既存ticket_type系
    if text_upper in {"EXACTA", "2車単", "2車単"}:
        return "exacta"
    if text_upper in {"TRIFECTA", "3連単", "３連単"}:
        return "trifecta"

    # bet_code系: 3=2車単, 5=3連単
    try:
        code = int(float(text))
        if code == 3:
            return "exacta"
        if code == 5:
            return "trifecta"
    except Exception:
        pass

    if "2車単" in text or "２車単" in text:
        return "exacta"
    if "3連単" in text or "３連単" in text:
        return "trifecta"
    return ""


def normalize_ticket_key_for_display(value) -> str:
    text = safe_text(value)
    text = re.sub(r"\s+", "", text)
    text = text.replace("=", "-")
    return text


# public01 car7 odds CSV helpers: car_1/car_2/car_3 + odds_1
def normalize_car_no_for_ticket(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return ""
    try:
        return str(int(float(text)))
    except Exception:
        return text


def build_ticket_label_from_car_columns(row: pd.Series, ticket_type: str) -> str:
    c1 = normalize_car_no_for_ticket(row.get("car_1", ""))
    c2 = normalize_car_no_for_ticket(row.get("car_2", ""))
    c3 = normalize_car_no_for_ticket(row.get("car_3", ""))

    if ticket_type == "exacta" and c1 and c2:
        return f"{c1}-{c2}"

    if ticket_type == "trifecta" and c1 and c2 and c3:
        return f"{c1}-{c2}-{c3}"

    return ""


def load_real_odds_popularity_source(date: str, race_id: str) -> pd.DataFrame:
    """実オッズ全体CSVから対象レースの2車単・3連単オッズを取得する。"""
    _, venue_id, race_no = parse_race_id(race_id)
    paths = find_real_odds_paths(date)
    if not paths:
        return pd.DataFrame()

    for path in paths:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty:
            continue

        venue_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code", "vel_code"])
        race_col = detect_column(df, ["race_no", "race_num", "race_number", "race"])
        bet_col = detect_column(df, ["ticket_type", "bet_type", "bet_type_ja", "type", "kind", "bet_code"])
        ticket_col = detect_column(df, ["ticket_label", "ticket_key", "combination", "numbers", "result_numbers", "line", "buy_key"])
        odds_col = detect_column(df, ["final_odds", "odds", "odds_value", "payout_odds", "popular_odds", "odds_1"])

        if venue_col is None or race_col is None or bet_col is None or odds_col is None:
            continue

        work = df.copy()
        work["__venue_id"] = pd.to_numeric(work[venue_col], errors="coerce")
        work["__race_no"] = work[race_col].map(normalize_race_no_value)
        work["ticket_type"] = work[bet_col].map(normalize_bet_type_for_popularity)

        if ticket_col is not None:
            work["ticket_label"] = work[ticket_col].map(normalize_ticket_key_for_display)
        elif {"car_1", "car_2"}.issubset(set(work.columns)):
            work["ticket_label"] = work.apply(
                lambda row: build_ticket_label_from_car_columns(row, row.get("ticket_type", "")),
                axis=1,
            )
        else:
            continue

        work["final_odds"] = pd.to_numeric(work[odds_col], errors="coerce")

        sub = work[
            (work["__venue_id"] == int(venue_id))
            & (work["__race_no"] == int(race_no))
            & (work["ticket_type"].isin(["exacta", "trifecta"]))
            & (work["ticket_label"] != "")
            & (work["final_odds"] > 0)
        ].copy()

        if not sub.empty:
            sub = sub[["ticket_type", "ticket_label", "final_odds"]].drop_duplicates(
                subset=["ticket_type", "ticket_label"],
                keep="last",
            )
            sub.attrs["source_path"] = str(path)
            return sub

    return pd.DataFrame()



def build_odds_popularity_html(race_df: pd.DataFrame) -> str:
    """実オッズ全体からオッズ人気上位（2車単・3連単）を表示する。"""
    import html

    if race_df.empty:
        return ""
    if "ticket_type" not in race_df.columns or "final_odds" not in race_df.columns:
        return ""

    labels = {"exacta": "2車単", "trifecta": "3連単"}

    sections = []
    work = race_df.copy()
    work["__final_odds"] = pd.to_numeric(work["final_odds"], errors="coerce")
    work = work.dropna(subset=["__final_odds"])
    work = work[work["__final_odds"] > 0]

    for ticket_type, title in labels.items():
        sub = work[work["ticket_type"].astype(str) == ticket_type].copy()
        if sub.empty:
            continue
        sub = sub.sort_values("__final_odds", ascending=True).head(3)

        rows = []
        for i, (_, row) in enumerate(sub.iterrows(), start=1):
            ticket_key = safe_text(row.get("ticket_label", row.get("ticket_key", "")), "--")
            odds = pd.to_numeric(row.get("__final_odds"), errors="coerce")
            odds_text = f"{float(odds):.1f}" if pd.notna(odds) else "--"
            rows.append(f"""
          <tr>
            <td style="font-weight:900; color:#475569; width:42px;">{i}位</td>
            <td style="font-weight:900;">{html.escape(ticket_key)}</td>
            <td style="font-weight:900; color:#b45309;">{html.escape(odds_text)}</td>
          </tr>""")

        sections.append(f"""
      <div style="min-width:240px; flex:1 1 260px;">
        <div style="font-weight:900; margin-bottom:6px; color:#1e3a8a;">{html.escape(title)}</div>
        <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>""")

    if not sections:
        return ""

    return f"""
  <div class="card">
    <div class="title">オッズ人気上位</div>
    <div style="display:flex; flex-wrap:wrap; gap:14px; align-items:flex-start;">
      {''.join(sections)}
    </div>
  </div>
"""

