#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
common_result.py

目的:
grade05 の結果・配当表示に関する共通処理。
主に build_race_pages.py から利用する。
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd

from scripts.public01.car9.common.utils import parse_race_id


def safe_text(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


class ResultItems(list):
    """複数払戻行を持ちながら、旧実装の dict.get(...) 呼び出しにも対応する。"""

    def get(self, key, default=None):
        if not self:
            return default
        first = self[0]
        if isinstance(first, dict):
            return first.get(key, default)
        return default


def load_result_payouts(date: str, race_id: str) -> dict:
    """結果払戻CSVから、対象レースの2車単/3連単/3連複を取得する。"""
    path = Path(f"data/public01/car9/results/public01_car9_results_{date}.csv")
    if not path.exists():
        return {}

    try:
        df = pd.read_csv(path)
    except Exception:
        return {}

    if df.empty:
        return {}

    _, venue_id, race_no = parse_race_id(race_id)
    required = {"venue_id", "race_no", "bet_type", "result_numbers", "payout_yen", "payout_odds"}
    if not required.issubset(set(df.columns)):
        return {}

    work = df.copy()
    work["venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
    work["race_no"] = pd.to_numeric(work["race_no"], errors="coerce")
    sub = work[(work["venue_id"] == int(venue_id)) & (work["race_no"] == int(race_no))].copy()
    if sub.empty:
        return {}

    result = {}
    for _, row in sub.iterrows():
        bet_type = safe_text(row.get("bet_type", ""))
        result_numbers = safe_text(row.get("result_numbers", ""))
        payout_yen = pd.to_numeric(row.get("payout_yen"), errors="coerce")
        payout_odds = pd.to_numeric(row.get("payout_odds"), errors="coerce")
        if not bet_type or not result_numbers:
            continue
        item = {
            "result_numbers": result_numbers,
            "payout_yen": int(payout_yen) if pd.notna(payout_yen) else None,
            "payout_odds": float(payout_odds) if pd.notna(payout_odds) else None,
        }
        if bet_type not in result:
            result[bet_type] = dict(item)
            result[bet_type]["_items"] = []
        result[bet_type]["_items"].append(item)

    return result


def normalize_ticket_key_for_compare(value: str, ticket_type: str) -> str:
    """買い目と結果を比較しやすい形式にそろえる。"""
    text = str(value or "").strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("=", "-")

    if ticket_type == "trio":
        nums = [x for x in text.split("-") if x]
        try:
            nums = sorted(nums, key=lambda x: int(x))
        except Exception:
            pass
        return "-".join(nums)

    return text


def get_result_items(result_payouts: dict, section_label: str) -> list[dict]:
    """Return result payout rows as a list. Supports old single-dict and new multi-row formats."""
    value = result_payouts.get(section_label)
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        items = value.get("_items")
        if isinstance(items, list):
            return items
        return [value]
    return []


def render_result_summary(result_payouts: dict, section_label: str, is_hit: bool = False) -> str:
    """タイトル行の横に表示する結果・配当テキストを作る。複数払戻行にも対応。"""
    result_items = get_result_items(result_payouts, section_label)
    if not result_items:
        return ""

    parts = []
    for result in result_items:
        numbers = html.escape(str(result.get("result_numbers", "")))
        payout_yen = result.get("payout_yen")
        payout_odds = result.get("payout_odds")

        if not numbers:
            continue

        payout_text = ""
        if payout_yen is not None:
            payout_text = f"{int(payout_yen):,}円"
        elif payout_odds is not None:
            payout_text = f"{float(payout_odds):.1f}"

        if payout_text:
            parts.append(f"{numbers}　{html.escape(payout_text)}")
        else:
            parts.append(numbers)

    if not parts:
        return ""

    hit_mark = "　🎯" if is_hit else ""
    text = " ／ ".join(parts) + hit_mark
    return f'<span style="display:inline-block; margin-left:10px; color:#b45309; font-weight:900;">{text}</span>'

# ==================== Ticket Rows for AI予想（買い目） ====================

def has_hit_ticket(sub: pd.DataFrame, ticket_type: str, result_payouts: dict, section_label: str) -> bool:
    """表示対象の買い目内に的中があるか判定する。複数払戻行にも対応。"""
    result_keys = {
        normalize_ticket_key_for_compare(item.get("result_numbers", ""), ticket_type)
        for item in get_result_items(result_payouts, section_label)
    }
    result_keys = {key for key in result_keys if key}
    if not result_keys:
        return False

    for _, row in sub.iterrows():
        ticket_key = str(row.get("ticket_label", row.get("ticket_key", "")))
        compare_key = normalize_ticket_key_for_compare(ticket_key, ticket_type)
        if compare_key in result_keys:
            return True

    return False


def build_ticket_rows(
    df: pd.DataFrame,
    top_exacta: int,
    top_trifecta: int,
    top_trio: int,
    result_payouts: dict | None = None,
) -> str:
    """AI予想（買い目）テーブルのtbody行HTMLを生成する。"""
    work = df.copy()
    result_payouts = result_payouts or {}
    work["probability_pct"] = pd.to_numeric(work["probability_pct"], errors="coerce").fillna(0)
    if "rank_in_race_type" in work.columns:
        work["rank_in_race_type"] = pd.to_numeric(
            work["rank_in_race_type"], errors="coerce"
        )

    rules = [
        ("exacta", top_exacta),
        ("trifecta", top_trifecta),
        ("trio", top_trio),
    ]

    frames = []
    for ticket_type, top_n in rules:
        sub = work[work["ticket_type"] == ticket_type].copy()
        if sub.empty or top_n <= 0:
            continue
        # 確率順で上位N件を取得。
        # probability同率時は保存済みrankをタイブレークに使い、
        # 公開買い目と的中判定の境界順位を固定する。
        if "rank_in_race_type" in sub.columns:
            sub = sub.sort_values(
                ["probability_pct", "rank_in_race_type"],
                ascending=[False, True],
                na_position="last",
                kind="stable",
            ).head(top_n)
        else:
            sub = sub.sort_values(
                "probability_pct",
                ascending=False,
                kind="stable",
            ).head(top_n)
        frames.append(sub)

    if frames:
        out = pd.concat(frames, axis=0, ignore_index=True)
    else:
        out = work.iloc[0:0].copy()

    ticket_order = {"exacta": 1, "trifecta": 2, "trio": 3}
    ticket_type_labels = {
        "exacta": "2車単",
        "trifecta": "3連単",
        "trio": "3連複",
    }

    if not out.empty:
        out["ticket_order"] = out["ticket_type"].map(ticket_order).fillna(99)
        # 表示順も同じタイブレーク規則に統一する
        if "rank_in_race_type" in out.columns:
            out = out.sort_values(
                ["ticket_order", "probability_pct", "rank_in_race_type"],
                ascending=[True, False, True],
                na_position="last",
                kind="stable",
            ).reset_index(drop=True)
        else:
            out = out.sort_values(
                ["ticket_order", "probability_pct"],
                ascending=[True, False],
                kind="stable",
            ).reset_index(drop=True)

    rows = []
    for ticket_type, _ in rules:
        sub = out[out["ticket_type"] == ticket_type].copy()
        if sub.empty:
            continue

        section_label_raw = ticket_type_labels.get(ticket_type, ticket_type)
        section_label = html.escape(section_label_raw)
        section_hit = has_hit_ticket(sub, ticket_type, result_payouts, section_label_raw)
        result_summary = render_result_summary(result_payouts, section_label_raw, is_hit=section_hit)
        rows.append(
            f"""
        <tr>
          <td colspan="3" style="background:#eef2ff; color:#1e3a8a; font-weight:800; text-align:left;">
            {section_label}{result_summary}
          </td>
        </tr>"""
        )

        for _, row in sub.iterrows():
            ticket_key = html.escape(str(row.get("ticket_label", row.get("ticket_key", ""))))
            probability_pct = float(row.get("probability_pct", 0))
            final_odds = pd.to_numeric(row.get("final_odds"), errors="coerce")

            odds_text = f"{final_odds:.1f}" if pd.notna(final_odds) else "--"

            compare_key = normalize_ticket_key_for_compare(ticket_key, ticket_type)
            section_result_items = get_result_items(result_payouts, ticket_type_labels.get(ticket_type, ticket_type))
            result_keys = {
                normalize_ticket_key_for_compare(item.get("result_numbers", ""), ticket_type)
                for item in section_result_items
            }
            result_keys = {key for key in result_keys if key}
            hit_style = ""
            if compare_key and compare_key in result_keys:
                hit_style = ' style="background:#fef3c7; color:#92400e; font-weight:900;"'

            rows.append(
                f"""
        <tr{hit_style}>
          <td>{ticket_key}</td>
          <td>{probability_pct:.2f}%</td>
          <td>{odds_text}</td>
        </tr>"""
            )

    return "\n".join(rows)
