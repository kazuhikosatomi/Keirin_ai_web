#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import html
import csv
from pathlib import Path

from scripts.public01.car7.common.arare import render_arare_badge
from scripts.public01.car7.common.ai_race import render_ai_race_analysis
from scripts.public01.car7.common.odds import calc_odds_status, render_odds_badge


# ==================== Race page basic text helpers ====================

def build_race_page_title_html(race_meta: dict) -> str:
    """レースページ上部タイトルHTMLを生成する。"""
    race_no = int(race_meta.get("race_no", 0))
    class_name = html.escape(str(race_meta.get("class_name", "")).strip())
    venue_name = html.escape(str(race_meta.get("venue_name", "")).strip())
    grade = html.escape(str(race_meta.get("grade", "")).strip())
    cup_name = html.escape(str(race_meta.get("cup_name", "")).strip())
    cup_day = html.escape(str(race_meta.get("cup_day", "")).strip())

    race_title = f"第{race_no}レース"
    if class_name:
        race_title += f"（{class_name}）"

    top_parts = [venue_name]
    if grade and grade.lower() != "nan":
        top_parts.append(grade)
    top_parts.append(html.escape(race_title))
    top_title = " ".join([p for p in top_parts if p and p.lower() != "nan"])

    bottom_title = cup_name
    if cup_day and cup_day.lower() != "nan":
        bottom_title = f"{bottom_title}（{cup_day}）" if bottom_title else f"（{cup_day}）"

    return (
        f'<span style="display:block; line-height:1.35;">{top_title}</span>'
        f'<span style="display:block; margin-top:6px; font-size:0.95rem; line-height:1.35; color:#dbeafe; font-weight:800;">{bottom_title}</span>'
    )



def is_watch_venue(date: str, race_meta: dict) -> bool:
    """対象レースの会場がWATCH対象かを返す。WATCH 0場の日はFalse。"""
    try:
        venue_id = int(float(str(race_meta.get("venue_id", "")).strip()))
    except Exception:
        return False

    path = (
        Path("data/public01/car7/config")
        / f"watch_targets_{date}.csv"
    )

    if not path.exists():
        return False

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw = str(row.get("venue_id", "")).strip()

                if not raw:
                    continue

                try:
                    if int(float(raw)) == venue_id:
                        return True
                except Exception:
                    continue
    except Exception:
        return False

    return False


def build_race_page_status_values(
    date: str,
    race_meta: dict,
    odds_update_time: str,
    odds_watch_status: str,
    arare_meta: dict,
    ai_race_meta: dict,
    other_finalize_time: str = "",
) -> dict:
    """レースページの基本ステータス表示値をまとめて生成する。"""
    post_time = html.escape(str(race_meta.get("post_time", "")))

    # 発走時刻から推測せず、実処理状態で表示する。
    watch_status = str(odds_watch_status or "").lower().strip()
    is_watch = is_watch_venue(date, race_meta)

    if is_watch:
        # WATCH:
        # 未取得 → 更新中 → 確定
        if not odds_update_time:
            odds_status = "オッズ未取得"
        elif watch_status == "done":
            odds_status = "オッズ確定"
        else:
            odds_status = "オッズ更新中"

        latest_time_text = (
            html.escape(odds_update_time)
            if odds_update_time
            else "--:--"
        )
    else:
        # OTHER:
        # 途中オッズ更新は行わないため、
        # 最終処理完了までは「オッズ未取得」。
        if watch_status == "done":
            odds_status = "オッズ確定"
            latest_time_text = (
                html.escape(other_finalize_time)
                if other_finalize_time
                else "--:--"
            )
        else:
            odds_status = "オッズ未取得"
            latest_time_text = "--:--"

    odds_badge = render_odds_badge(odds_status)

    # 発走予定横のオッズ時刻も実取得時刻を使用する。
    # OTHER未確定時は --:--。
    if is_watch or watch_status == "done":
        display_odds_time = (
            html.escape(odds_update_time)
            if odds_update_time
            else "--:--"
        )
    else:
        display_odds_time = "--:--"

    odds_time_text = (
        f'　<span style="font-weight:700;">'
        f'オッズ更新：{display_odds_time}'
        f'</span>'
    )

    arare_badge = render_arare_badge(arare_meta)
    ai_race_analysis = render_ai_race_analysis(ai_race_meta)

    return {
        "post_time": post_time,
        "odds_status": odds_status,
        "odds_badge": odds_badge,
        "latest_time_text": latest_time_text,
        "odds_time_text": odds_time_text,
        "arare_badge": arare_badge,
        "ai_race_analysis": ai_race_analysis,
    }


def apply_basic_template_values(template: str, page_title_html: str, status_values: dict) -> str:
    """テンプレートの基本テキスト部分を実データに差し替える。"""
    post_time = status_values["post_time"]
    odds_status = status_values["odds_status"]
    odds_badge = status_values["odds_badge"]
    latest_time_text = status_values["latest_time_text"]
    odds_time_text = status_values["odds_time_text"]
    arare_badge = status_values["arare_badge"]
    ai_race_analysis = status_values["ai_race_analysis"]

    out = template
    out = out.replace("サンプル競輪場 00R", page_title_html)
    out = out.replace('<span class="badge waiting">オッズ更新待ち</span>', odds_badge)
    out = out.replace("オッズ更新待ち", odds_status)
    out = out.replace("発走予定：--:--", f"発走予定：{post_time or '--:--'}{odds_time_text}")

    # 買い目が出た後の監視更新では、レースページにもオッズ更新時刻を必ず反映する
    out = out.replace(
        '<div class="label">最終更新</div>\n          <div class="value">--:--</div>',
        f'<div class="label">最終更新</div>\n          <div class="value">{latest_time_text}</div>'
    )

    out = out.replace(
        '<span class="badge arare">荒れ度 --</span>',
        ai_race_analysis,
    )
    out = out.replace(
        "荒れ度 --",
        ai_race_analysis,
    )
    return out


def replace_basic_text(
    template: str,
    race_id: str,
    race_meta: dict,
    odds_update_time: str,
    odds_watch_status: str,
    arare_meta: dict,
    ai_race_meta: dict,
    date: str,
    other_finalize_time: str = "",
) -> str:
    """サンプル表記を実データに差し替える。"""
    page_title_html = build_race_page_title_html(race_meta)
    status_values = build_race_page_status_values(
        date,
        race_meta,
        odds_update_time,
        odds_watch_status,
        arare_meta,
        ai_race_meta,
        other_finalize_time,
    )
    return apply_basic_template_values(template, page_title_html, status_values)
