#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_venue_index_pages.py

目的:
grade05 の開催一覧ページを生成する。

入力:
- data/bet01/car7/step43/bet01_car7_step43_all_top_tickets_YYYY-MM-DD.csv
- data/entries/YYYY/entry_YYYY-MM-DD.csv
- data/arare02/...（荒れ度）
- data/public01/car7/watch/...（オッズ更新・的中メタ）
- data/master/...（競輪場データ）

出力:
- tmp/public01/car7/latest/snapshot/vXX/index.html      # 競輪場別ページ
- tmp/public01/car7/latest/snapshot/latest.json          # トップページ用リンク情報

重要:
- venue_index_template.html はデザイン原本なので上書きしない
- latest/snapshot/vXX/index.html / latest/snapshot/latest.json は出力用なので毎回上書きしてOK
- 2開催以上ある日は venue_id ごとに一覧を分けて表示する
"""

from __future__ import annotations

import json

import argparse
import html
import re
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.public01.car7.common.constants import VENUE_NAME_MAP
from scripts.public01.car7.common.utils import (
    determine_active_race_from_odds_terms,
    load_entry_meta,
    parse_race_id,
)

from scripts.public01.car7.common.result import (
    load_result_payouts,
    normalize_ticket_key_for_compare,
)
from scripts.public01.car7.common.venue_profile import (
    build_venue_tactics_summary_html,
    load_venue_bank_master,
    load_venue_tactics_summary,
)
from scripts.public01.car7.common.odds import (
    calc_odds_status,
    latest_update_text,
    load_odds_meta,
    render_odds_badge,
)
from scripts.public01.car7.common.ai_race import (
    load_ai_race_meta,
    chance_stars,
)
from scripts.public01.car7.common.config import TOP_PAGE_URL
from scripts.public01.car7.common.hit import (
    load_hit_meta,
    render_hit_badge,
)


# ==================== Config ====================

DEFAULT_DATE = pd.Timestamp.today().strftime("%Y-%m-%d")
TEMPLATE_PATH = Path("docs/grade05/venue_index_template.html")
SNAPSHOT_DIR = Path("tmp/public01/car7/latest/snapshot")



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--verbose", action="store_true", help="詳細ログを表示する")
    parser.add_argument(
        "--no-profit",
        action="store_true",
        help="開催途中用。レース一覧下部の収支集計を表示しない",
    )
    return parser.parse_args()


def load_step43(date: str) -> pd.DataFrame:
    path = Path(f"data/bet01/car7/step43/bet01_car7_step43_all_top_tickets_{date}.csv")
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"step43 is empty: {path}")
    # sim08 race_id normalize
    # YYYY-MM-DD_v45_r1 -> YYYY-MM-DD_45_1
    if "race_id" in df.columns:
        df["race_id"] = (
            df["race_id"]
            .astype(str)
            .str.replace(
                r"_v(\d+)_r(\d+)$",
                r"_\1_\2",
                regex=True,
            )
        )

    return df


def insert_after_summary_card(template: str, insert_html: str) -> str:
    if not insert_html:
        return template
    marker = "</section>\n\n    <section class=\"venue-card\">"
    if marker in template:
        return template.replace(marker, f"</section>\n\n{insert_html}\n    <section class=\"venue-card\">", 1)
    return template





def format_yen(value) -> str:
    """金額をカンマ付きで表示する。"""
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "0"


def format_profit(value) -> str:
    """収支を符号付きで表示する。"""
    try:
        amount = int(float(value))
    except Exception:
        amount = 0
    sign = "+" if amount > 0 else ""
    return f"{sign}{amount:,}"


def load_profit_summary(date: str) -> pd.DataFrame:
    """日別収支サマリーCSVを読み込む。"""
    path = Path(f"data/public01/car7/summary/public01_car7_profit_summary_{date}.csv")
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()



def normalize_venue_id_value(value) -> str:
    text = str(value or "").strip().removeprefix("v")
    if not text or text.lower() == "nan":
        return ""
    try:
        return str(int(float(text)))
    except Exception:
        return text


def build_profit_summary_html(date: str, venue_ids: list[str] | None = None) -> str:
    """レース一覧下部に表示する収支テーブルHTMLを生成する。"""
    df = load_profit_summary(date)
    if df.empty:
        return ""

    if venue_ids is not None and "venue_id" in df.columns:
        venue_id_set = {normalize_venue_id_value(v) for v in venue_ids}
        df = df[df["venue_id"].map(normalize_venue_id_value).isin(venue_id_set)].copy()
    elif "venue_id" in df.columns:
        df = df[df["venue_id"].astype(str) == "ALL"].copy()

    if df.empty:
        return ""

    required = {"bet_type", "hit_count", "race_count", "buy_amount", "payout_amount", "profit"}
    if not required.issubset(set(df.columns)):
        return ""

    if "return_rate_pct" not in df.columns:
        df = df.copy()
        buy = pd.to_numeric(df["buy_amount"], errors="coerce").fillna(0)
        payout = pd.to_numeric(df["payout_amount"], errors="coerce").fillna(0)
        df["return_rate_pct"] = [
            round((p / b) * 100, 1) if b else 0.0
            for p, b in zip(payout, buy)
        ]

    total_row = df[df["bet_type"].astype(str) == "Total"]
    total_summary_html = ""
    if not total_row.empty:
        total = total_row.iloc[0]
        total_profit = int(pd.to_numeric(total.get("profit"), errors="coerce") or 0)
        total_return_rate = float(pd.to_numeric(total.get("return_rate_pct"), errors="coerce") or 0)
        total_profit_color = "#dc2626" if total_profit >= 0 else "#2563eb"
        total_summary_html = f"""
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:8px 0 12px;">
        <div style="background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:10px 12px;">
          <div style="font-size:0.78rem; color:#64748b; font-weight:800;">Total回収率</div>
          <div style="font-size:1.45rem; line-height:1.25; font-weight:900; color:#1e3a8a;">{total_return_rate:.1f}%</div>
        </div>
        <div style="background:#f8fafc; border:1px solid #e5e7eb; border-radius:12px; padding:10px 12px;">
          <div style="font-size:0.78rem; color:#64748b; font-weight:800;">Total収支</div>
          <div style="font-size:1.45rem; line-height:1.25; font-weight:900; color:{total_profit_color};">{format_profit(total.get('profit'))}</div>
        </div>
      </div>
"""

    rows = []
    order = ["2車単", "3連単", "3連複", "Total"]
    work = df.copy()
    work["__order"] = work["bet_type"].map({name: i for i, name in enumerate(order)}).fillna(99)
    work = work.sort_values("__order")

    for _, row in work.iterrows():
        bet_type = str(row.get("bet_type", ""))
        hit_count = int(pd.to_numeric(row.get("hit_count"), errors="coerce") or 0)
        race_count = int(pd.to_numeric(row.get("race_count"), errors="coerce") or 0)
        profit = int(pd.to_numeric(row.get("profit"), errors="coerce") or 0)
        return_rate = float(pd.to_numeric(row.get("return_rate_pct"), errors="coerce") or 0)
        profit_color = "#dc2626" if profit >= 0 else "#2563eb"
        font_weight = "900" if bet_type == "Total" else "800"
        bg = "#f8fafc" if bet_type == "Total" else "#ffffff"

        rows.append(f"""
          <tr style="background:{bg}; font-weight:{font_weight};">
            <td style="text-align:center; white-space:nowrap;">{html.escape(bet_type)}</td>
            <td style="text-align:center; white-space:nowrap;">{hit_count}/{race_count}</td>
            <td style="text-align:right; white-space:nowrap;">{format_yen(row.get('buy_amount'))}</td>
            <td style="text-align:right; white-space:nowrap;">{format_yen(row.get('payout_amount'))}</td>
            <td style="text-align:right; white-space:nowrap; color:{profit_color};">{format_profit(row.get('profit'))}</td>
            <td style="text-align:right; white-space:nowrap;">{return_rate:.1f}%</td>
          </tr>""")

    if not rows:
        return ""

    return f"""
    <section class="summary-card">
      <h2>💰 買い目収支</h2>
      {total_summary_html}
      <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; font-size:0.76rem; table-layout:fixed;">
          <thead>
            <tr>
              <th style="text-align:center; background:#f1f5f9;">賭式</th>
              <th style="text-align:center; background:#f1f5f9;">的中</th>
              <th style="text-align:right; background:#f1f5f9;">購入</th>
              <th style="text-align:right; background:#f1f5f9;">払戻</th>
              <th style="text-align:right; background:#f1f5f9;">収支</th>
              <th style="text-align:right; background:#f1f5f9;">回収率</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>
      <div style="margin-top:8px; color:#64748b; font-size:0.78rem; line-height:1.45;">
        ※ 2車単2点・3連単5点・3連複3点を各100円購入した想定です。スマホでは詳細表を小さめに表示しています。
      </div>
    </section>
"""


def insert_before_footer(template: str, insert_html: str) -> str:
    """main末尾の直前にHTMLを挿入する。"""
    if not insert_html:
        return template
    marker = "\n  </main>"
    if marker in template:
        return template.replace(marker, f"\n{insert_html}\n  </main>", 1)
    return template


def build_event_title(meta: pd.DataFrame, venue_ids: list[str]) -> str:
    """開催タイトルを生成する。例: 松阪 GⅢ アクアリッズカップＧ３ナイター（2日目）"""
    titles = []
    for venue_id_text in venue_ids:
        venue_id = int(venue_id_text)
        sub = meta[meta["venue_id"] == venue_id] if not meta.empty and "venue_id" in meta.columns else pd.DataFrame()
        venue_name = VENUE_NAME_MAP.get(venue_id, f"v{venue_id}")
        grade = ""
        cup_name = ""
        cup_day = ""

        if not sub.empty:
            row = sub.iloc[0]
            venue_name = str(row.get("venue_name", venue_name)).strip() or venue_name
            grade = str(row.get("grade", "")).strip()
            cup_name = str(row.get("cup_name", "")).strip()
            cup_day = str(row.get("cup_day", "")).strip()

        parts = [venue_name]
        if grade and grade.lower() != "nan":
            parts.append(grade)
        if cup_name and cup_name.lower() != "nan":
            parts.append(cup_name)

        title = " ".join(parts).strip()
        if cup_day and cup_day.lower() != "nan":
            title = f"{title}（{cup_day}）" if title else f"（{cup_day}）"
        if title:
            titles.append(title)

    return " / ".join(titles)


def build_rows(
    date: str,
    df: pd.DataFrame,
    entry_meta: pd.DataFrame,
    odds_meta: pd.DataFrame,
    hit_meta: pd.DataFrame,
    active_venue_id: int | None,
    active_race_no: int | None,
    venue_page: bool = False,
) -> str:
    race_ids = sort_race_ids_numeric(
        df["race_id"].astype(str).unique()
    )

    # WATCH対象外（OTHER）は途中オッズ更新を行わない。
    # 最終処理完了までは「オッズ未取得」、
    # odds_status=done 後だけ「オッズ確定」と表示する。
    watch_venue_ids = load_watch_venue_ids(date)

    venue_blocks = {}

    for race_id in race_ids:
        _, venue_id, race_no = parse_race_id(race_id)
        venue_id_int = int(venue_id)
        race_no_int = int(race_no)
        if venue_page:
            link = f"./races/r{race_no:02d}.html"
        else:
            link = f"./v{venue_id}/races/r{race_no:02d}.html"

        post_time = "--:--"
        class_name = ""
        if not entry_meta.empty:
            sub = entry_meta[(entry_meta["venue_id"] == venue_id_int) & (entry_meta["race_no"] == race_no_int)]
            if not sub.empty:
                post_time_value = str(sub.iloc[0].get("post_time", "")).strip()
                if post_time_value:
                    post_time = post_time_value
                class_name_value = str(sub.iloc[0].get("class_name", "")).strip()
                if class_name_value and class_name_value.lower() != "nan":
                    class_name = class_name_value

        class_name_html = ""
        if class_name:
            class_name_html = f'<span style="display:inline-block; margin-left:10px; font-size:0.85rem; color:#4b5563; font-weight:800; white-space:nowrap;">{class_name}</span>'

        chance_badge = ""
        chance_meta = load_ai_race_meta(date, venue_id_int, race_no_int)
        chance_prob = chance_meta.get("chance_prob", pd.NA) if chance_meta else pd.NA

        if pd.notna(chance_prob):
            stars = chance_stars(float(chance_prob))
            chance_badge = (
                '<span style="display:inline-block; margin-right:8px; '
                'font-size:0.85rem; font-weight:800; white-space:nowrap;">'
                f'AI荒れ指数 {stars}</span>'
            )

        odds_update_time = ""
        term_odds_status = ""
        if not odds_meta.empty:
            odds_sub = odds_meta[
                (odds_meta["venue_id"] == venue_id_int)
                & (odds_meta["race_no"] == race_no_int)
            ]
            if not odds_sub.empty:
                odds_update_time = str(
                    odds_sub.iloc[0].get("odds_update_time", "")
                ).strip()
                term_odds_status = str(
                    odds_sub.iloc[0].get("odds_status", "")
                ).strip()

        is_watch_venue = venue_id_int in watch_venue_ids

        if is_watch_venue:
            # WATCHは従来どおり
            # 未取得 → 更新中 → 確定
            odds_status = calc_odds_status(
                parse_race_id(race_id)[0],
                post_time,
                odds_update_time,
                term_odds_status,
            )
        else:
            # OTHERは途中更新しないため、
            # 最終処理が完了するまで「未取得」とする。
            odds_status = (
                "オッズ確定"
                if term_odds_status == "done"
                else "オッズ未取得"
            )

        odds_badge = render_odds_badge(odds_status)

        hit_badge_html = ""
        if not hit_meta.empty:
            # race_id文字列形式には依存しない。
            # legacy形式 / bet01形式のどちらでも、
            # venue_id + race_no で同一レースとして照合する。
            hit_sub = hit_meta[
                hit_meta["race_id"]
                .astype(str)
                .map(
                    lambda rid:
                        int(parse_race_id(rid)[1])
                        == int(venue_id_int)
                        and
                        int(parse_race_id(rid)[2])
                        == int(race_no_int)
                )
            ]

            if not hit_sub.empty:
                hit_badge_html = render_hit_badge(
                    hit_sub.iloc[0].get(
                        "hit_types",
                        "",
                    )
                )

        race_label = f"{race_no}R{class_name_html}{hit_badge_html}"
        row_class = "race-row"
        row_style = ""
        is_active_race = (
            active_venue_id is not None
            and active_race_no is not None
            and int(venue_id_int) == int(active_venue_id)
            and int(race_no_int) == int(active_race_no)
        )
        if is_active_race:
            row_class = "race-row active-race-row"
            row_style = (
                ' style="background:#fff7ed; border:2px solid #fb923c; '
                'box-shadow:0 0 0 3px rgba(251,146,60,0.16);"'
            )

        row_html = f"""
        <div class="{row_class}"{row_style}>
          <div class="race-no">{race_label}</div>
          <div>
            <div>
              {chance_badge}
              {odds_badge}
            </div>
            <div class="race-meta">発走予定 {post_time}</div>
          </div>
          <a class="race-link" href="{link}">買い目を見る</a>
        </div>"""

        if venue_id_int not in venue_blocks:
            venue_name = VENUE_NAME_MAP.get(venue_id_int, f"v{venue_id_int}")

            if not entry_meta.empty:
                venue_sub = entry_meta[entry_meta["venue_id"] == venue_id_int]
                if not venue_sub.empty:
                    candidate = str(venue_sub.iloc[0].get("venue_name", "")).strip()
                    if candidate and candidate.lower() != "nan":
                        venue_name = candidate

            venue_blocks[venue_id_int] = {
                "venue_name": venue_name,
                "rows": [],
            }

        venue_blocks[venue_id_int]["rows"].append(row_html)

    html_blocks = []

    for venue_id in sorted(venue_blocks.keys()):
        venue_name = venue_blocks[venue_id]["venue_name"]
        venue_rows = "\n".join(venue_blocks[venue_id]["rows"])

        block_html = f"""
    <section class="venue-card">
      <h2>{venue_name}</h2>
      <div class="race-list">
{venue_rows}
      </div>
    </section>
"""

        html_blocks.append(block_html)

    return "\n".join(html_blocks)


def replace_race_list(template: str, rows_html: str) -> str:
    """テンプレ内の既存 venue-card 全体を、生成済みのレース一覧HTMLに差し替える。"""
    pattern = re.compile(
        r'\n\s*<section class="venue-card">.*?</section>',
        flags=re.DOTALL,
    )

    new_html, count = pattern.subn("\n" + rows_html, template, count=1)
    if count != 1:
        raise ValueError('target <section class="venue-card"> block not found in template')
    return new_html


def update_summary_values(template: str, date: str, df: pd.DataFrame, entry_meta: pd.DataFrame, odds_meta: pd.DataFrame) -> str:
    race_ids = sort_race_ids_numeric(
        df["race_id"].astype(str).unique()
    )
    venue_ids = sorted({parse_race_id(race_id)[1] for race_id in race_ids})

    event_title = build_event_title(entry_meta, venue_ids)

    # grade05共通テンプレートの表示文言をcar7専用に置換する。
    # 共通テンプレート本体はcar9/grade05でも使用するため変更しない。
    template = template.replace(
        "グレードレース予想 | 競輪AIアタルくん",
        "7車レース予想 | 競輪AIアタルくん",
    )
    template = template.replace(
        "🏆 グレードレース予想",
        "🏆 7車レース予想",
    )
    template = template.replace(
        "📅 本日のグレードレース",
        "📅 本日の7車レース",
    )

    out = template.replace("YYYY-MM-DD", date)
    out = out.replace('<div class="value">0</div>', f'<div class="value">{len(venue_ids)}</div>', 1)
    out = out.replace('<div class="value">0R</div>', f'<div class="value">{len(race_ids)}R</div>', 1)

    # 会場単位の最終更新時刻。
    # OTHERは途中オッズ更新を行わないため、
    # 全Rの最終処理が完了するまでは --:--、
    # 完了後のみ最終オッズ取得時刻を表示する。
    update_text = "--:--"

    if len(venue_ids) == 1 and not odds_meta.empty:
        venue_id_int = int(venue_ids[0])

        venue_odds_meta = odds_meta.copy()
        if "venue_id" in venue_odds_meta.columns:
            venue_odds_meta = venue_odds_meta[
                pd.to_numeric(
                    venue_odds_meta["venue_id"],
                    errors="coerce",
                ) == venue_id_int
            ].copy()

        watch_venue_ids = load_watch_venue_ids(date)
        is_watch_venue = venue_id_int in watch_venue_ids

        if is_watch_venue:
            update_text = latest_update_text(venue_odds_meta)
        else:
            # OTHERは全R完了後のみ、専用の最終処理完了時刻を表示する。
            if (
                not venue_odds_meta.empty
                and "odds_status" in venue_odds_meta.columns
                and venue_odds_meta["odds_status"]
                    .astype(str)
                    .eq("done")
                    .all()
            ):
                if "other_finalize_time" in venue_odds_meta.columns:
                    times = (
                        venue_odds_meta["other_finalize_time"]
                        .astype(str)
                        .str.strip()
                    )
                    times = times[times != ""]
                    if not times.empty:
                        update_text = times.iloc[-1]

    else:
        # 複数会場をまとめたページでは従来どおり。
        update_text = latest_update_text(odds_meta)

    out = out.replace(
        '<div class="label">最終更新</div>\n          <div class="value">--:--</div>',
        f'<div class="label">最終更新</div>\n          <div class="value">{update_text}</div>',
    )

    if event_title:
        out = out.replace(
            "<h2>📅 本日の7車レース</h2>",
            f'<h2>📅 本日の7車レース <span style="display:inline-block; margin-left:8px; padding:4px 10px; border-radius:999px; background:#fee2e2; color:#991b1b; font-weight:900;">{event_title}</span></h2>',
        )
        out = out.replace("<h2>サンプル競輪場</h2>", f"<h2>{event_title}</h2>")

    return out


def load_watch_venue_ids(date: str) -> set[int]:
    """当日のリアルタイムWATCH対象venue_idを返す。"""
    path = Path(
        f"data/public01/car7/config/watch_targets_{date}.csv"
    )

    if not path.exists():
        return set()

    df = pd.read_csv(path)

    if df.empty or "venue_id" not in df.columns:
        return set()

    return set(
        pd.to_numeric(df["venue_id"], errors="coerce")
        .dropna()
        .astype(int)
        .tolist()
    )


def write_latest_json(date: str):
    """docsトップ用に、対象日と開催別 index ページへのリンク情報をJSON出力する。"""
    watch_venue_ids = load_watch_venue_ids(date)
    latest_items = []
    root = SNAPSHOT_DIR

    for index_path in sorted(root.glob("v*/index.html")):
        venue_id = index_path.parent.name
        try:
            html_text = index_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        title = ""
        m = re.search(r'<h2[^>]*>📅\s*本日の7車レース\s*<span[^>]*>(.*?)</span>', html_text, re.DOTALL)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1))
            title = re.sub(r"\s+", " ", title).strip()

        if not title:
            m = re.search(r'<title[^>]*>(.*?)</title>', html_text, re.DOTALL)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1))
                title = re.sub(r"\s+", " ", title).strip()
                title = title.replace("競輪AIアタルくん", "").replace("|", "").strip()

        if not title:
            title = venue_id

        venue_number = int(str(venue_id).lstrip("v"))

        latest_items.append({
            "venue_id": venue_id,
            "title": title,
            "href": f"./public/latest/car7/{venue_id}/index.html",
            "publish_group": (
                "watch"
                if venue_number in watch_venue_ids
                else "other"
            ),
        })

    latest_json_path = root / "latest.json"
    latest_json_path.write_text(
        json.dumps(
            {
                "date": date,
                "items": latest_items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"💾 saved: {latest_json_path}")

    # -----------------------------------------------------
    # WATCH対象 / その他 の会場一覧ページを生成
    # -----------------------------------------------------
    group_settings = {
        "watch": {
            "title": "本日のAI予想：7車",
            "description": "WATCH対象の7車開催",
        },
        "other": {
            "title": "その他の7車予想",
            "description": "その他の7車開催",
        },
    }

    for group_name, group_meta in group_settings.items():
        group_items = [
            item
            for item in latest_items
            if item.get("publish_group") == group_name
        ]

        cards = []

        for item in group_items:
            venue_id = item["venue_id"]
            title = item["title"]

            cards.append(
                f"""
                <a class="venue-card" href="../{venue_id}/index.html">
                  <div class="venue-title">{title}</div>
                  <div class="venue-link">予想を見る →</div>
                </a>
                """
            )

        if cards:
            cards_html = "\n".join(cards)
        else:
            cards_html = """
              <div class="empty-message">
                本日の対象開催はありません。
              </div>
            """

        group_dir = root / group_name
        group_dir.mkdir(parents=True, exist_ok=True)

        group_html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{group_meta["title"]} | 競輪AIアタルくん</title>
  <style>
    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2937;
      font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Hiragino Kaku Gothic ProN",
        "Yu Gothic",
        sans-serif;
    }}

    .container {{
      width: min(900px, calc(100% - 28px));
      margin: 0 auto;
      padding: 24px 0 40px;
    }}

    .back-link {{
      display: inline-block;
      margin-bottom: 18px;
      color: #374151;
      font-weight: 700;
      text-decoration: none;
    }}

    h1 {{
      margin: 0 0 6px;
      font-size: 1.6rem;
    }}

    .description {{
      margin: 0 0 22px;
      color: #6b7280;
      font-size: 0.95rem;
    }}

    .venue-list {{
      display: grid;
      gap: 12px;
    }}

    .venue-card {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 14px;
      color: inherit;
      text-decoration: none;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    .venue-title {{
      font-size: 1.05rem;
      font-weight: 800;
    }}

    .venue-link {{
      flex: 0 0 auto;
      color: #dc2626;
      font-size: 0.9rem;
      font-weight: 800;
    }}

    .empty-message {{
      padding: 24px;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 14px;
      text-align: center;
      color: #6b7280;
      font-weight: 700;
    }}

    @media (max-width: 560px) {{
      .venue-card {{
        padding: 16px;
      }}

      .venue-title {{
        font-size: 1rem;
      }}
    }}
  </style>
</head>
<body>
  <main class="container">
    <a class="back-link" href="../../../../index.html">← 一覧へ戻る</a>

    <h1>{group_meta["title"]}</h1>
    <p class="description">{group_meta["description"]}</p>

    <div class="venue-list">
      {cards_html}
    </div>
  </main>
</body>
</html>
"""

        group_index_path = group_dir / "index.html"
        group_index_path.write_text(
            group_html,
            encoding="utf-8",
        )

        print(
            f"💾 saved: {group_index_path} "
            f"({len(group_items)} venues)"
        )


def sort_race_ids_numeric(race_ids):
    """race_idを会場番号・レース番号の数値順にする。"""

    def sort_key(race_id):
        try:
            _, venue_id, race_no = parse_race_id(
                str(race_id)
            )
            return (
                int(venue_id),
                int(race_no),
            )
        except Exception:
            return (
                9999,
                9999,
            )

    return sorted(
        [str(race_id) for race_id in race_ids],
        key=sort_key,
    )


def main():
    args = parse_args()
    date = args.date

    print("=" * 72)
    print(f"🚀 START public01 car7 build venue index pages | date={date}")
    print("=" * 72)

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(TEMPLATE_PATH)

    df = load_step43(date)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    entry_meta = load_entry_meta(date)
    odds_meta = load_odds_meta(date)
    hit_meta = load_hit_meta(date)

    race_ids = sort_race_ids_numeric(
        df["race_id"].astype(str).unique()
    )
    venue_ids = sorted({parse_race_id(race_id)[1] for race_id in race_ids})
    # Log event and venue/race counts before generating output
    event_title = build_event_title(entry_meta, venue_ids)
    if event_title:
        print(f"📍 event: {event_title}")
    print(f"📊 venues: {len(venue_ids)} / races: {len(race_ids)}")
    tactics_summary = load_venue_tactics_summary(date, venue_ids)
    bank_meta = load_venue_bank_master()
    tactics_summary_html = build_venue_tactics_summary_html(tactics_summary, entry_meta, venue_ids, bank_meta)
    active_venue_id, active_race_no = determine_active_race_from_odds_terms(date, grade_name="grade05")

    def render_venue_index_html(target_df: pd.DataFrame) -> str:
        target_race_ids = sort_race_ids_numeric(
            target_df["race_id"].astype(str).unique()
        )
        target_venue_ids = sorted({parse_race_id(race_id)[1] for race_id in target_race_ids})

        target_entry_meta = entry_meta[entry_meta["venue_id"].isin([int(v) for v in target_venue_ids])].copy()
        target_odds_meta = odds_meta[odds_meta["venue_id"].isin([int(v) for v in target_venue_ids])].copy()
        target_hit_meta = hit_meta[hit_meta["race_id"].astype(str).map(lambda rid: int(parse_race_id(rid)[1]) in [int(v) for v in target_venue_ids])].copy() if not hit_meta.empty else hit_meta

        target_tactics_summary = tactics_summary[tactics_summary["venue_id"].isin([int(v) for v in target_venue_ids])].copy()
        target_tactics_summary_html = build_venue_tactics_summary_html(
            target_tactics_summary,
            target_entry_meta,
            target_venue_ids,
            bank_meta,
        )

        target_rows_html = build_rows(
            date,
            target_df,
            target_entry_meta,
            target_odds_meta,
            target_hit_meta,
            active_venue_id,
            active_race_no,
            venue_page=True,
        )

        out_html = update_summary_values(template, date, target_df, target_entry_meta, target_odds_meta)
        out_html = insert_after_summary_card(out_html, target_tactics_summary_html)
        out_html = replace_race_list(out_html, target_rows_html)
        if not args.no_profit:
            out_html = insert_before_footer(
                out_html,
                build_profit_summary_html(date, target_venue_ids),
            )

        # 会場ページの「一覧へ戻る」は閲覧元の一覧へ戻す。
        # snapshot/vXX/index.html から、
        # WATCH会場 -> ../watch/
        # OTHER会場 -> ../other/
        watch_venue_ids = load_watch_venue_ids(date)

        if (
            len(target_venue_ids) == 1
            and int(target_venue_ids[0]) in watch_venue_ids
        ):
            top_href = "../watch/"
        else:
            top_href = "../other/"

        out_html = out_html.replace("{{TOP_HREF}}", top_href)

        # public01では「トップ」ではなく、閲覧元の一覧へ戻る表記に統一
        out_html = out_html.replace("← トップへ戻る", "← 一覧へ戻る")
        out_html = out_html.replace(
            "荒れ度・買い目・発走前オッズをまとめて確認できます",
            "AI荒れ指数・買い目・発走前オッズをまとめて確認できます",
        )

        return out_html

    # (unused, removed)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    for venue_id in venue_ids:
        venue_df = df[df["race_id"].astype(str).map(lambda rid: int(parse_race_id(rid)[1])) == int(venue_id)].copy()
        if venue_df.empty:
            continue
        venue_html = render_venue_index_html(venue_df)
        venue_output_path = SNAPSHOT_DIR / f"v{int(venue_id)}" / "index.html"
        venue_output_path.parent.mkdir(parents=True, exist_ok=True)
        venue_output_path.write_text(venue_html, encoding="utf-8")
        print(f"💾 saved: {venue_output_path}")

    if args.verbose:
        print(f"📄 template: {TEMPLATE_PATH}")
        print(f"📊 entry_meta rows: {len(entry_meta)}")
        if "cup_name" in entry_meta.columns:
            print(f"📊 entry_meta cup_name rows: {entry_meta['cup_name'].astype(str).str.strip().ne('').sum()}")
        print(f"📊 odds_meta rows: {len(odds_meta)}")
        print(f"📊 hit_meta rows: {len(hit_meta)}")
        print(f"📊 tactics_summary rows: {len(tactics_summary)}")
        print(f"📊 bank_meta rows: {len(bank_meta)}")
    write_latest_json(date)
    print(f"🎉 END public01 car7 build venue index pages | date={date}")
    print("=" * 72)


if __name__ == "__main__":
    main()
