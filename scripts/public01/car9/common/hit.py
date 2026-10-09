#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
hit.py

grade05 共通の的中メタ情報ユーティリティ。
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from scripts.public01.car9.common.utils import detect_column
from scripts.public01.car9.common.result import (
    load_result_payouts,
    normalize_ticket_key_for_compare,
)


DISPLAY_TICKET_LIMITS = {
    "2車単": 5,
    "3連単": 10,
    "3連複": 5,
}


def find_ticket_source_path(date: str) -> Path | None:
    """
    public01 car9 の的中判定は、
    実際にレースページ表示へ使用している
    bet01/car9 Step43 を唯一の正本とする。

    旧 grade05 / watch / sim06 系の買い目は使用しない。
    """
    path = Path(
        f"data/bet01/car9/step43/"
        f"bet01_car9_step43_all_top_tickets_{date}.csv"
    )

    if path.exists():
        return path

    return None


def normalize_bet_type_ja(value) -> str:
    text = str(value or "").strip()
    if text in {"exacta", "2車単", "二車単"}:
        return "2車単"
    if text in {"trifecta", "3連単", "三連単"}:
        return "3連単"
    if text in {"trio", "3連複", "三連複"}:
        return "3連複"
    return text

def normalize_bet_type_code(value) -> str:
    text = str(value or "").strip()
    if text in {"exacta", "2車単", "二車単"}:
        return "exacta"
    if text in {"trifecta", "3連単", "三連単"}:
        return "trifecta"
    if text in {"trio", "3連複", "三連複"}:
        return "trio"
    return text


# race_id の末尾R有無や小数表記を吸収して比較用に正規化する
def normalize_race_id_for_compare(value) -> str:
    """race_id の末尾R有無や小数表記を吸収して比較用に正規化する。"""
    s = str(value or "").strip()
    if not s:
        return ""

    parts = s.split("_")
    if len(parts) < 3:
        return s

    last = str(parts[-1]).strip()
    if last.endswith("R"):
        last = last[:-1]

    try:
        last = str(int(float(last)))
    except Exception:
        pass

    parts[-1] = last
    return "_".join(parts)

def extract_result_key(value, ticket_type: str = "") -> str:
    ticket_type_code = normalize_bet_type_code(ticket_type)
    if isinstance(value, dict):
        for key in ["ticket_key", "result_key", "combination", "result_numbers", "numbers", "key"]:
            if key in value and str(value.get(key, "")).strip():
                return normalize_ticket_key_for_compare(value.get(key, ""), ticket_type_code)
    return normalize_ticket_key_for_compare(value, ticket_type_code)

def flatten_result_payouts(result_payouts) -> dict[str, list[str]]:
    """common_result.load_result_payouts の返り値を {bet_type_ja: [normalized_key, ...]} に寄せる。

    同着では同じ券種に複数の払戻組み合わせが存在するため、
    1件に上書きせず全結果を保持する。
    """
    out: dict[str, list[str]] = {}

    if isinstance(result_payouts, dict):
        for bet_type, payload in result_payouts.items():
            bet_type_ja = normalize_bet_type_ja(bet_type)
            if not bet_type_ja:
                continue

            # 同着では load_result_payouts() が _items に
            # 同一券種の複数払戻を保持している。
            items = payload.get("_items", []) if isinstance(payload, dict) else []

            if isinstance(items, list) and items:
                candidates = items
            else:
                candidates = [payload]

            for item in candidates:
                result_key = extract_result_key(item, bet_type_ja)
                if not result_key:
                    continue

                out.setdefault(bet_type_ja, [])
                if result_key not in out[bet_type_ja]:
                    out[bet_type_ja].append(result_key)

        return out

    if isinstance(result_payouts, pd.DataFrame) and not result_payouts.empty:
        bet_col = detect_column(result_payouts, ["ticket_type_ja", "bet_type_ja", "bet_type", "type"])
        key_col = detect_column(result_payouts, ["ticket_key", "result_key", "combination", "result_numbers", "numbers"])
        if bet_col and key_col:
            for _, row in result_payouts.iterrows():
                bet_type_ja = normalize_bet_type_ja(row.get(bet_col, ""))
                result_key = normalize_ticket_key_for_compare(row.get(key_col, ""), normalize_bet_type_code(bet_type_ja))
                if bet_type_ja and result_key:
                    out.setdefault(bet_type_ja, [])
                    if result_key not in out[bet_type_ja]:
                        out[bet_type_ja].append(result_key)
    return out

def load_hit_meta(date: str) -> pd.DataFrame:
    """todayページ用に、race_idごとの的中賭け式を集計する。"""
    ticket_path = find_ticket_source_path(date)
    if ticket_path is None:
        return pd.DataFrame(columns=["race_id", "hit_types"])

    try:
        tickets = pd.read_csv(ticket_path, dtype=str).fillna("")
        if "race_id" in tickets.columns:
            tickets["_race_id_norm"] = tickets["race_id"].map(normalize_race_id_for_compare)
    except Exception:
        return pd.DataFrame(columns=["race_id", "hit_types"])

    if tickets.empty or "race_id" not in tickets.columns:
        return pd.DataFrame(columns=["race_id", "hit_types"])

    bet_col = detect_column(tickets, ["ticket_type_ja", "bet_type_ja", "ticket_type", "bet_type"])
    key_col = detect_column(tickets, ["ticket_key", "combination", "numbers", "buy_key"])
    if bet_col is None or key_col is None:
        return pd.DataFrame(columns=["race_id", "hit_types"])

    rows = []
    bet_order = ["2車単", "3連単", "3連複"]

    for race_id, sub in tickets.groupby("_race_id_norm", sort=True):
        try:
            result_payouts = load_result_payouts(str(date), str(race_id))
        except TypeError:
            try:
                result_payouts = load_result_payouts(str(race_id))
            except Exception:
                result_payouts = {}
        except Exception:
            result_payouts = {}

        result_map = flatten_result_payouts(result_payouts)
        if not result_map:
            continue

        hit_types = []
        for bet_type_ja in bet_order:
            result_keys = result_map.get(bet_type_ja, [])
            if not result_keys:
                continue

            bet_sub = sub[sub[bet_col].map(normalize_bet_type_ja) == bet_type_ja].copy()
            if bet_sub.empty:
                continue

            # todayの的中表示は、watch全買い目ではなく
            # レースページに実際表示している買い目だけを対象にする。
            display_limit = DISPLAY_TICKET_LIMITS.get(bet_type_ja)
            if display_limit:
                # レースページで実際に表示する買い目と
                # 的中判定対象を完全一致させる。
                #
                # レースページと同じ選定規則を使用する。
                # probability降順、同率時はrank_in_race_type昇順。
                prob_col = detect_column(
                    bet_sub,
                    [
                        "probability_pct",
                        "probability",
                        "prob",
                    ],
                )
                rank_col = detect_column(
                    bet_sub,
                    ["rank_in_race_type"],
                )

                if prob_col:
                    bet_sub["_prob_sort"] = pd.to_numeric(
                        bet_sub[prob_col],
                        errors="coerce",
                    ).fillna(0)

                    sort_cols = ["_prob_sort"]
                    ascending = [False]

                    if rank_col:
                        bet_sub["_rank_sort"] = pd.to_numeric(
                            bet_sub[rank_col],
                            errors="coerce",
                        )
                        sort_cols.append("_rank_sort")
                        ascending.append(True)

                    bet_sub = (
                        bet_sub
                        .sort_values(
                            sort_cols,
                            ascending=ascending,
                            na_position="last",
                            kind="stable",
                        )
                        .head(display_limit)
                        .copy()
                    )
                elif rank_col:
                    # probability列がない旧データでは正式rankを使用。
                    bet_sub["_rank_sort"] = pd.to_numeric(
                        bet_sub[rank_col],
                        errors="coerce",
                    )

                    bet_sub = (
                        bet_sub
                        .sort_values(
                            "_rank_sort",
                            ascending=True,
                            na_position="last",
                            kind="stable",
                        )
                        .head(display_limit)
                        .copy()
                    )
                else:
                    bet_sub = (
                        bet_sub
                        .head(display_limit)
                        .copy()
                    )

            ticket_type_code = normalize_bet_type_code(bet_type_ja)
            ticket_keys = bet_sub[key_col].map(lambda v: normalize_ticket_key_for_compare(v, ticket_type_code))
            if ticket_keys.isin(result_keys).any():
                hit_types.append(bet_type_ja)

        if hit_types:
            hit_text = "・".join(hit_types)
            race_id_base = str(race_id)

            rows.append({
                "race_id": race_id_base,
                "hit_types": hit_text,
            })

            parts = race_id_base.split("_")
            if len(parts) >= 3:
                try:
                    race_no_int = int(float(parts[-1].replace("R", "")))
                except Exception:
                    race_no_int = None

                if race_no_int is not None:
                    race_id_with_r = "_".join(parts[:-1] + [str(race_no_int) + "R"])
                    race_id_with_zero_r = "_".join(parts[:-1] + [f"{race_no_int:02d}R"])

                    for rid in [race_id_with_r, race_id_with_zero_r]:
                        rows.append({
                            "race_id": rid,
                            "hit_types": hit_text,
                        })

    if not rows:
        return pd.DataFrame(columns=["race_id", "hit_types"])

    return pd.DataFrame(rows)

def render_hit_badge(hit_types: str) -> str:
    text = str(hit_types or "").strip()
    if not text:
        return ""
    return (
        '<span style="display:inline-block; margin-left:8px; '
        'font-size:0.82rem; color:#dc2626; font-weight:900; white-space:nowrap;">'
        f'🎯 {html.escape(text)}'
        '</span>'
    )


