#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step01_generate_sample_race_html.py

目的:
step43 の買い目CSVを読み込み、デザイン済みの r00_template.html に
買い目データだけを差し込んで r00.html を生成する。

重要:
- r00_template.html はデザイン原本なので上書きしない
- r00.html は出力用なので毎回上書きしてOK
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd


DEFAULT_DATE = "2026-04-26"
DEFAULT_TEMPLATE_PATH = Path("docs/grade/races/v00/r00_template.html")
DEFAULT_OUTPUT_PATH = Path("docs/grade/races/v00/r00.html")

GRADE_SYMBOL_MAP = {
    "G1": "GⅠ",
    "G2": "GⅡ",
    "G3": "GⅢ",
    "F1": "FⅠ",
    "F2": "FⅡ",
    "GP": "GP",
}

VENUE_NAME_MAP = {
    11: "函館",
    12: "青森",
    13: "いわき平",
    21: "弥彦",
    22: "前橋",
    23: "取手",
    24: "宇都宮",
    25: "大宮",
    26: "西武園",
    27: "京王閣",
    28: "立川",
    31: "松戸",
    32: "千葉",
    34: "川崎",
    35: "平塚",
    36: "小田原",
    37: "伊東",
    38: "静岡",
    42: "名古屋",
    43: "岐阜",
    44: "大垣",
    45: "豊橋",
    46: "富山",
    47: "松阪",
    48: "四日市",
    51: "福井",
    53: "奈良",
    54: "向日町",
    55: "和歌山",
    56: "岸和田",
    61: "玉野",
    62: "広島",
    63: "防府",
    71: "高松",
    73: "小松島",
    74: "高知",
    75: "松山",
    81: "小倉",
    83: "久留米",
    84: "武雄",
    85: "佐世保",
    86: "別府",
    87: "熊本",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--race-id", default=None, help="対象race_id。未指定ならCSV先頭のrace_id")
    parser.add_argument("--top-exacta", type=int, default=5, help="2車単の表示件数")
    parser.add_argument("--top-trifecta", type=int, default=10, help="3連単の表示件数")
    parser.add_argument("--top-trio", type=int, default=5, help="3連複の表示件数")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE_PATH), help="HTMLテンプレート")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="出力HTML")
    return parser.parse_args()


def load_ticket_source(date: str) -> pd.DataFrame:
    """step04のオッズ結合済みCSVを優先し、無ければstep43を読む。"""
    step04_path = Path(f"data/grade01/step04/grade01_step04_tickets_with_odds_{date}.csv")
    step43_path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")

    if step04_path.exists():
        path = step04_path
        source_name = "step04_with_odds"
    elif step43_path.exists():
        path = step43_path
        source_name = "step43_no_odds"
    else:
        raise FileNotFoundError(f"ticket source not found: {step04_path} or {step43_path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"ticket source is empty: {path}")

    df.attrs["source_path"] = str(path)
    df.attrs["source_name"] = source_name
    return df


# ------------------- Helper functions for race meta -------------------


def parse_race_id(race_id: str):
    # 例: 2026-04-26_42_04R
    parts = str(race_id).split("_")
    date = parts[0]
    venue_id = int(parts[1])
    race_no = int(parts[2].replace("R", ""))
    return date, venue_id, race_no


# ------------------- Race page navigation HTML -------------------
def build_race_page_nav_html(date: str, current_race_id: str) -> str:
    """同日の他レース詳細ページへ移動するためのリンクを生成する。"""
    step43_path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")
    if not step43_path.exists():
        return ""

    try:
        nav_df = pd.read_csv(step43_path)
    except Exception:
        return ""

    if nav_df.empty or "race_id" not in nav_df.columns:
        return ""

    race_ids = sorted(nav_df["race_id"].astype(str).unique())
    if not race_ids:
        return ""

    links = []
    for rid in race_ids:
        try:
            _, venue_id, race_no = parse_race_id(rid)
        except Exception:
            continue

        label = f"{race_no}R"
        href = f"../v{venue_id}/r{race_no:02d}.html"

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
    <div class="title" style="margin-bottom:8px;">レース移動</div>
    <div style="display:flex; flex-wrap:wrap; align-items:center;">
      {''.join(links)}
    </div>
  </div>
"""


def detect_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def normalize_time_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if ":" in text:
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                hour = int(float(parts[0]))
                minute = int(float(parts[1]))
                return f"{hour:02d}:{minute:02d}"
            except Exception:
                return text
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) == 4:
        return f"{int(digits[:2]):02d}:{int(digits[2:]):02d}"
    if len(digits) == 3:
        return f"{int(digits[:1]):02d}:{int(digits[1:]):02d}"
    return text


def find_entry_path(date: str) -> Path | None:
    year = date[:4]
    candidates = [
        Path(f"data/entries/{year}/entry_{date}.csv"),
        Path(f"data/entry/{year}/entry_{date}.csv"),
        Path(f"data/entries/entry_{date}.csv"),
        Path(f"data/entry_{date}.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def normalize_grade(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper().replace("Ｇ", "G").replace("Ｆ", "F")
    return GRADE_SYMBOL_MAP.get(upper, text)


def load_race_meta(date: str, race_id: str) -> dict:
    """entryファイルから競輪場名・グレード・発走予定を取得する。"""
    _, venue_id, race_no = parse_race_id(race_id)
    meta = {
        "venue_id": venue_id,
        "race_no": race_no,
        "venue_name": VENUE_NAME_MAP.get(venue_id, f"v{venue_id}"),
        "grade": "",
        "class_name": "",
        "cup_name": "",
        "post_time": "",
    }

    entry_path = find_entry_path(date)
    if entry_path is None:
        return meta

    df = pd.read_csv(entry_path)
    if df.empty:
        return meta

    venue_id_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code"])
    venue_name_col = detect_column(df, ["venue_name", "place_name", "jyo_name", "競輪場", "場名"])
    race_col = detect_column(df, ["race_no", "race_num", "race_number", "race"])
    time_col = detect_column(df, ["post_time", "start_time", "race_time", "発走時間", "発走時刻", "締切時刻"])
    grade_col = detect_column(df, ["race_grade", "grade", "grade_name", "グレード", "レースグレード"])
    class_name_col = detect_column(df, ["class_name", "race_class", "race_class_name", "class", "レース種別", "競走種目"])
    cup_name_col = detect_column(df, ["cup_name", "cup", "cup_title", "開催名"])

    if venue_id_col is None or race_col is None:
        return meta

    work = df.copy()
    work["__venue_id"] = pd.to_numeric(work[venue_id_col], errors="coerce")
    work["__race_no"] = pd.to_numeric(work[race_col], errors="coerce")
    sub = work[(work["__venue_id"] == venue_id) & (work["__race_no"] == race_no)].copy()
    if sub.empty:
        return meta

    row = sub.iloc[0]
    if venue_name_col:
        venue_name = str(row.get(venue_name_col, "")).strip()
        if venue_name:
            meta["venue_name"] = venue_name
    if grade_col:
        meta["grade"] = normalize_grade(row.get(grade_col, ""))
    if class_name_col:
        class_name = str(row.get(class_name_col, "")).strip()
        if class_name and class_name.lower() != "nan":
            meta["class_name"] = class_name
    if cup_name_col:
        cup_name = str(row.get(cup_name_col, "")).strip()
        if cup_name and cup_name.lower() != "nan":
            meta["cup_name"] = cup_name
    if time_col:
        meta["post_time"] = normalize_time_text(row.get(time_col, ""))

    return meta



def load_odds_update_time(date: str, race_id: str) -> str:
    """step05のterm_tableからオッズ取得時刻を取得する。"""
    path = Path(f"data/grade01/step05/grade01_step05_odds_term_table_{date}.csv")
    if not path.exists():
        return ""
    df = pd.read_csv(path, dtype=str).fillna("")
    if "race_id" not in df.columns:
        return ""
    sub = df[df["race_id"].astype(str) == str(race_id)]
    if sub.empty:
        return ""
    row = sub.iloc[0]
    fetched_at = str(row.get("fetched_at", "")).strip()
    if fetched_at:
        dt = pd.to_datetime(fetched_at, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%H:%M")
    return ""


# ---- Odds popularity: Use real odds CSV, not just AI tickets ----
def find_real_odds_paths(date: str) -> list[Path]:
    year = str(date)[:4]
    candidates = [
        Path(f"data/grade01/step07/grade01_step07_odds_{date}.csv"),
        Path(f"data/grade01/step07/grade01_step07_odds_for_race_{date}.csv"),
        Path(f"data/grade01/step07/odds_{date}.csv"),
        Path(f"data/grade01/odds/{year}/grade01_odds_{date}.csv"),
        Path(f"data/grade01/odds/grade01_odds_{date}.csv"),
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


# --- New: Helper functions for grade01 odds CSV with car_1/car_2/car_3 and odds_1 ---
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


# ---- New odds status helpers ----
def calc_odds_status(date: str, post_time: str, odds_update_time: str) -> str:
    """オッズ取得状態を表示用に判定する。"""
    post_time_text = normalize_time_text(post_time)
    now_dt = pd.Timestamp.now()

    # 発走時刻が不明な場合
    if not post_time_text:
        return "オッズ更新中"

    post_dt = pd.to_datetime(f"{date} {post_time_text}", errors="coerce")

    if pd.isna(post_dt):
        return "オッズ更新中"

    # 発走前は全て「更新中」にする
    if now_dt < post_dt:
        return "オッズ更新中"

    # 発走後でまだオッズ取得されていない場合も「更新中」
    if not odds_update_time:
        return "オッズ更新中"

    # 取得済みなら確定
    return "オッズ確定"


def render_odds_badge(odds_status: str) -> str:
    if odds_status == "オッズ確定":
        style = "background:#dcfce7; color:#166534;"
    elif odds_status == "オッズ更新中":
        style = "background:#dbeafe; color:#1e40af;"
    else:
        style = "background:#e5e7eb; color:#374151;"
    return f'<span class="badge waiting" style="{style}">{html.escape(odds_status)}</span>'


def find_arare_path(date: str) -> Path | None:
    candidates = [
        Path(f"data/arare02/pred_logs/pred_{date}.csv"),
        Path(f"data/arare02/pred_logs/arare02_pred_{date}.csv"),
        Path(f"data/arare02/pred_logs/arare02_predictions_{date}.csv"),
        Path(f"data/arare02/predictions/arare02_predictions_{date}.csv"),
        Path(f"data/arare02/latest/arare02_predictions_{date}.csv"),
        Path("data/arare02/latest/arare02_predictions_latest.csv"),
        Path("data/arare02/work/arare02_step09_predictions.csv"),
        Path("data/arare02/work/arare02_step10_predictions.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_arare_meta(date: str, race_id: str) -> dict:
    arare_path = find_arare_path(date)
    if arare_path is None:
        return {"arare_prob": None, "arare_index": None, "arare_level": None}

    arare = pd.read_csv(arare_path)
    if arare.empty:
        return {"arare_prob": None, "arare_index": None, "arare_level": None}

    target_date, target_venue_id, target_race_no = parse_race_id(race_id)

    date_col = detect_column(arare, ["date", "race_date"])
    venue_col = detect_column(arare, ["venue_id", "place_id", "jyocode", "jyo_code"])
    race_col = detect_column(arare, ["race_no", "race_num", "race_number", "race"])
    race_id_col = detect_column(arare, ["race_id"])
    prob_col = detect_column(arare, ["arare_prob", "pred_arare_prob", "pred_prob", "probability", "prob_is_arare"])

    if prob_col is None:
        return {"arare_prob": None, "arare_index": None, "arare_level": None}

    work = arare.copy()
    if venue_col is None or race_col is None:
        if race_id_col is None:
            return {"arare_prob": None, "arare_index": None, "arare_level": None}
        parsed = work[race_id_col].astype(str).map(parse_race_id)
        work["__date"] = parsed.map(lambda x: x[0])
        work["__venue_id"] = parsed.map(lambda x: x[1])
        work["__race_no"] = parsed.map(lambda x: x[2])
    else:
        if date_col:
            work["__date"] = work[date_col].astype(str)
        else:
            work["__date"] = target_date
        work["__venue_id"] = pd.to_numeric(work[venue_col], errors="coerce")
        work["__race_no"] = pd.to_numeric(work[race_col], errors="coerce")

    work["__prob"] = pd.to_numeric(work[prob_col], errors="coerce")
    sub = work[
        (work["__date"].astype(str) == str(target_date))
        & (work["__venue_id"] == int(target_venue_id))
        & (work["__race_no"] == int(target_race_no))
    ].dropna(subset=["__prob"])

    if sub.empty:
        return {"arare_prob": None, "arare_index": None, "arare_level": None}

    arare_prob = float(sub.iloc[0]["__prob"])
    arare_index = int(round(arare_prob * 100))
    if arare_prob >= 0.50:
        arare_level = "高"
    elif arare_prob >= 0.30:
        arare_level = "中"
    else:
        arare_level = "低"

    return {
        "arare_prob": arare_prob,
        "arare_index": arare_index,
        "arare_level": arare_level,
    }


def render_arare_badge(arare_meta: dict) -> str:
    arare_index = arare_meta.get("arare_index")
    arare_level = arare_meta.get("arare_level")
    if arare_index is None or arare_level is None:
        return '<span class="badge arare">荒れ度 --</span>'

    level = str(arare_level).strip()
    if level == "高":
        style = "background:#fee2e2; color:#991b1b;"
    elif level == "中":
        style = "background:#dcfce7; color:#166534;"
    else:
        style = "background:#dbeafe; color:#1e40af;"

    return f'<span class="badge arare" style="{style}">荒れ度 {int(arare_index)}</span>'


def safe_int(value, default: int = 0) -> int:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return default
    return int(num)



def safe_pct(value, default: float = 0.0) -> str:
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        num = default
    return f"{float(num) * 100:.1f}%"


# --- Result payouts helpers ---

def load_result_payouts(date: str, race_id: str) -> dict:
    """Step09の結果払戻CSVから、対象レースの2車単/3連単/3連複を取得する。"""
    path = Path(f"data/grade01/step09/grade01_step09_results_{date}.csv")
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
        result[bet_type] = {
            "result_numbers": result_numbers,
            "payout_yen": int(payout_yen) if pd.notna(payout_yen) else None,
            "payout_odds": float(payout_odds) if pd.notna(payout_odds) else None,
        }

    return result


def normalize_ticket_key_for_compare(value: str, ticket_type: str) -> str:
    """買い目と結果を比較しやすい形式にそろえる。"""
    text = str(value or "").strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("=", "-")

    # 3連複は順不同なので昇順にする
    if ticket_type == "trio":
        nums = [x for x in text.split("-") if x]
        try:
            nums = sorted(nums, key=lambda x: int(x))
        except Exception:
            pass
        return "-".join(nums)

    return text


def render_result_summary(result_payouts: dict, section_label: str) -> str:
    """タイトル行の横に表示する結果・配当テキストを作る。"""
    result = result_payouts.get(section_label)
    if not result:
        return ""

    numbers = html.escape(str(result.get("result_numbers", "")))
    payout_yen = result.get("payout_yen")
    payout_odds = result.get("payout_odds")

    payout_text = ""
    if payout_yen is not None:
        payout_text = f"{int(payout_yen):,}円"
    elif payout_odds is not None:
        payout_text = f"{float(payout_odds):.1f}"

    if not numbers:
        return ""

    if payout_text:
        return f'<span style="display:inline-block; margin-left:10px; color:#b45309; font-weight:900;">{numbers}　{html.escape(payout_text)}</span>'
    return f'<span style="display:inline-block; margin-left:10px; color:#b45309; font-weight:900;">{numbers}</span>'


# ------------------- Additional helper functions for racer info -------------------

def safe_text(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def get_prefecture_short(row: pd.Series) -> str:
    """都道府県名を2文字程度で表示する。"""
    for col in ["prefecture", "prefecture_name", "ken", "県", "府県"]:
        if col in row.index:
            text = safe_text(row.get(col, ""))
            if text:
                return text[:2]
    return ""


def get_racer_term(row: pd.Series) -> str:
    """期別を表示する。"""
    for col in ["term", "racer_term", "期", "期別"]:
        if col in row.index:
            text = safe_text(row.get(col, ""))
            if text:
                return text
    return ""



# Helper to normalize race_no values robustly
def normalize_race_no_value(value) -> int | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None



# Style rows by car_no for visual distinction
def car_row_style(car_no: int) -> str:
    styles = {
        1: "background:#ffffff; color:#111827;",
        2: "background:#e5e7eb; color:#111827;",
        3: "background:#fee2e2; color:#111827;",
        4: "background:#dbeafe; color:#111827;",
        5: "background:#fef9c3; color:#111827;",
        6: "background:#dcfce7; color:#111827;",
        7: "background:#ffedd5; color:#111827;",
        8: "background:#fce7f3; color:#111827;",
        9: "background:#ede9fe; color:#111827;",
    }
    return styles.get(int(car_no), "")


# 並び予想用の車番バッジ色
def car_badge_style(car_no: int) -> tuple[str, str, str]:
    """並び予想用の車番バッジ色。戻り値: background, color, border"""
    styles = {
        1: ("#ffffff", "#111827", "1px solid #d1d5db"),
        2: ("#222222", "#ffffff", "1px solid #222222"),
        3: ("#dc2626", "#ffffff", "1px solid #dc2626"),
        4: ("#2563eb", "#ffffff", "1px solid #2563eb"),
        5: ("#facc15", "#111827", "1px solid #facc15"),
        6: ("#16a34a", "#ffffff", "1px solid #16a34a"),
        7: ("#ea580c", "#ffffff", "1px solid #ea580c"),
        8: ("#db2777", "#ffffff", "1px solid #db2777"),
        9: ("#7c3aed", "#ffffff", "1px solid #7c3aed"),
    }
    return styles.get(int(car_no), ("#e5e7eb", "#111827", "1px solid #d1d5db"))


def build_lineup_html(df: pd.DataFrame) -> str:
    """line_id / line_pos から並び予想を表示する。"""
    if df.empty:
        return ""

    required = {"car_no", "line_id", "line_pos"}
    if not required.issubset(set(df.columns)):
        return ""

    work = df.copy()
    work["car_no"] = pd.to_numeric(work["car_no"], errors="coerce")
    work["line_id"] = pd.to_numeric(work["line_id"], errors="coerce")
    work["line_pos"] = pd.to_numeric(work["line_pos"], errors="coerce")
    work = work.dropna(subset=["car_no", "line_id", "line_pos"])
    if work.empty:
        return ""

    work["car_no"] = work["car_no"].astype(int)
    work["line_id"] = work["line_id"].astype(int)
    work["line_pos"] = work["line_pos"].astype(int)
    work = work.sort_values(["line_id", "line_pos", "car_no"])

    line_blocks = []
    for _, sub in work.groupby("line_id", sort=True):
        badges = []
        for car_no in sub["car_no"].tolist():
            bg, fg, border = car_badge_style(car_no)
            badges.append(
                f'<span style="display:inline-flex; align-items:center; justify-content:center; '
                f'width:22px; height:22px; border-radius:4px; margin-right:2px; '
                f'background:{bg}; color:{fg}; border:{border}; '
                f'font-weight:900; font-size:0.78rem; line-height:1;">{car_no}</span>'
            )
        line_blocks.append(
            '<span style="display:inline-flex; align-items:center; margin:0 12px 6px 0; flex:0 0 auto;">'
            + "".join(badges)
            + "</span>"
        )

    if not line_blocks:
        return ""

    return f"""
  <div class="card">
    <div class="title">並び予想</div>
    <div style="display:flex; flex-wrap:nowrap; align-items:center; gap:0; overflow-x:auto; white-space:nowrap;">
      <span style="font-size:1.05rem; font-weight:900; margin-right:6px; color:#374151; flex:0 0 auto;">←</span>
      {''.join(line_blocks)}
    </div>
  </div>
"""


# --- Odds popularity best 3 card ---
def build_odds_popularity_html(race_df: pd.DataFrame) -> str:
    """実オッズ全体からオッズ人気上位（2車単・3連単）を表示する。"""
    if race_df.empty:
        return ""
    if "ticket_type" not in race_df.columns or "final_odds" not in race_df.columns:
        return ""

    labels = {
        "exacta": "2車単",
        "trifecta": "3連単",
    }

    sections = []
    work = race_df.copy()
    work["__final_odds"] = pd.to_numeric(work["final_odds"], errors="coerce")
    work = work.dropna(subset=["__final_odds"])
    work = work[work["__final_odds"] > 0]
    if work.empty:
        return ""

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
            rows.append(
                f"""
          <tr>
            <td style="font-weight:900; color:#475569; width:42px;">{i}位</td>
            <td style="font-weight:900;">{html.escape(ticket_key)}</td>
            <td style="font-weight:900; color:#b45309;">{html.escape(odds_text)}</td>
          </tr>"""
            )

        if rows:
            sections.append(
                f"""
      <div style="min-width:240px; flex:1 1 260px;">
        <div style="font-weight:900; margin-bottom:6px; color:#1e3a8a;">{html.escape(title)}</div>
        <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
      </div>"""
            )

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


def load_racer_stats_table(date: str, race_id: str) -> pd.DataFrame:
    path = Path(f"data/sim06/step12/sim06_step12_first_predict_features_{date}.csv")
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
        return sub

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
            return sub

    return pd.DataFrame()


def build_racer_stats_html(df: pd.DataFrame) -> str:
    if df.empty:
        return ""

    rows = []
    for _, r in df.sort_values("car_no").iterrows():
        car_no = safe_int(r.get("car_no", 0))
        race_count = safe_int(r.get("racer_race_count_1y", 0))
        top3_count = safe_int(r.get("racer_top3_count_1y", 0))
        out_count = max(race_count - top3_count, 0)
        row_style = car_row_style(car_no)
        prefecture_short = get_prefecture_short(r)
        racer_term = get_racer_term(r)

        rows.append(f"""
        <tr style="{row_style}">
          <td>{car_no}</td>
          <td style="min-width:92px; white-space:nowrap;">{html.escape(str(r.get('name_kanji', '')))}</td>
          <td style="min-width:32px; white-space:nowrap;">{html.escape(prefecture_short)}</td>
          <td style="min-width:32px; white-space:nowrap;">{html.escape(racer_term)}</td>
          <td>{race_count}</td>
          <td>{safe_int(r.get('racer_S_count_1y_reference', 0))}</td>
          <td>{safe_int(r.get('racer_B_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_tactic_nige_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_tactic_makuri_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_tactic_sashi_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_tactic_mark_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_win_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_second_count_1y', 0))}</td>
          <td>{safe_int(r.get('racer_third_count_1y', 0))}</td>
          <td>{out_count}</td>
          <td>{safe_pct(r.get('racer_win_rate_1y', 0))}</td>
          <td>{safe_pct(r.get('racer_second_rate_1y', 0))}</td>
          <td>{safe_pct(r.get('racer_third_rate_1y', 0))}</td>
        </tr>""")

    return f"""
  <div class="card">
    <div class="title">選手成績（グレードレース 過去1年）</div>
    <div style="overflow-x:auto;">
      <table>
        <thead>
          <tr>
            <th>No</th><th style="min-width:92px; white-space:nowrap;">氏名</th><th style="min-width:32px; white-space:nowrap;">府県</th><th style="min-width:32px; white-space:nowrap;">期</th><th>出走</th><th>S</th><th>B</th>
            <th>逃</th><th>捲</th><th>差</th><th>マ</th>
            <th>1着</th><th>2着</th><th>3着</th><th>外</th>
            <th>1率</th><th>2率</th><th>3率</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
  </div>
"""

def build_ticket_rows(
    df: pd.DataFrame,
    top_exacta: int,
    top_trifecta: int,
    top_trio: int,
    result_payouts: dict | None = None,
) -> str:
    work = df.copy()
    result_payouts = result_payouts or {}
    work["probability_pct"] = pd.to_numeric(work["probability_pct"], errors="coerce").fillna(0)

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
        # 確率順で上位N件を取得（rankではなくprobabilityで制御）
        sub = sub.sort_values("probability_pct", ascending=False).head(top_n)
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
        # 表示順も確率順に変更
        out = out.sort_values(["ticket_order", "probability_pct"], ascending=[True, False]).reset_index(drop=True)

    rows = []
    for ticket_type, _ in rules:
        sub = out[out["ticket_type"] == ticket_type].copy()
        if sub.empty:
            continue

        section_label_raw = ticket_type_labels.get(ticket_type, ticket_type)
        section_label = html.escape(section_label_raw)
        result_summary = render_result_summary(result_payouts, section_label_raw)
        rows.append(
            f"""
        <tr>
          <td colspan="3" style="background:#eef2ff; color:#1e3a8a; font-weight:800; text-align:left;">
            {section_label}{result_summary}
          </td>
        </tr>"""
        )

        for _, row in sub.iterrows():
            ticket_type_ja = html.escape(str(row.get("ticket_type_ja", "")))
            ticket_key = html.escape(str(row.get("ticket_label", row.get("ticket_key", ""))))
            probability_pct = float(row.get("probability_pct", 0))
            final_odds = pd.to_numeric(row.get("final_odds"), errors="coerce")

            odds_text = f"{final_odds:.1f}" if pd.notna(final_odds) else "--"

            compare_key = normalize_ticket_key_for_compare(ticket_key, ticket_type)
            result_for_section = result_payouts.get(ticket_type_labels.get(ticket_type, ticket_type), {})
            result_key = normalize_ticket_key_for_compare(result_for_section.get("result_numbers", ""), ticket_type)
            hit_style = ""
            if result_key and compare_key == result_key:
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


def replace_first_tbody_after_heading(template: str, heading_text: str, tbody_html: str) -> str:
    """
    指定見出しの後にある最初の <tbody>...</tbody> だけを差し替える。
    今回は「AI予想（買い目）」カード内のtbodyを対象にする。
    """
    heading_pos = template.find(heading_text)
    if heading_pos == -1:
        raise ValueError(f"heading not found in template: {heading_text}")

    before = template[:heading_pos]
    after = template[heading_pos:]

    pattern = re.compile(r"<tbody>.*?</tbody>", flags=re.DOTALL)
    replacement = f"<tbody>\n{tbody_html}\n      </tbody>"
    after_new, count = pattern.subn(replacement, after, count=1)

    if count != 1:
        raise ValueError("target tbody not found after heading")

    return before + after_new


def replace_basic_text(template: str, race_id: str, race_meta: dict, odds_update_time: str, arare_meta: dict, date: str) -> str:
    """サンプル表記を実データに差し替える。"""
    venue_name = html.escape(str(race_meta.get("venue_name", "")))
    grade = html.escape(str(race_meta.get("grade", "")))
    race_no = int(race_meta.get("race_no", 0))
    class_name = html.escape(str(race_meta.get("class_name", "")).strip())
    cup_name = html.escape(str(race_meta.get("cup_name", "")).strip())
    post_time = html.escape(str(race_meta.get("post_time", "")))

    title_parts = [venue_name]
    if grade:
        title_parts.append(grade)
    race_title = f"第{race_no}レース"
    if class_name:
        race_title += f"（{class_name}）"
    title_parts.append(race_title)
    page_title = " ".join([p for p in title_parts if p])
    page_title_html = page_title
    if cup_name:
        page_title_html = (
            f'<span style="display:block; line-height:1.35;">{page_title}</span>'
            f'<span style="display:block; margin-top:6px; font-size:0.95rem; line-height:1.35; color:#dbeafe; font-weight:800;">{cup_name}</span>'
        )

    odds_status = calc_odds_status(date, post_time, odds_update_time)
    odds_badge = render_odds_badge(odds_status)
    odds_time_text = ""
    if odds_update_time:
        odds_time_text = f" / オッズ {html.escape(odds_update_time)}現在"

    arare_badge = render_arare_badge(arare_meta)

    out = template
    out = out.replace("サンプル競輪場 00R", page_title_html)
    out = out.replace('<span class="badge waiting">オッズ更新待ち</span>', odds_badge)
    out = out.replace("オッズ更新待ち", odds_status)
    out = out.replace("発走予定：--:--", f"発走予定：{post_time or '--:--'}{odds_time_text}")
    out = out.replace('<span class="badge arare">荒れ度 --</span>', arare_badge)
    out = out.replace("荒れ度 --", arare_badge)
    return out


def main():
    args = parse_args()
    date = args.date
    template_path = Path(args.template)
    output_path = Path(args.output)

    print("=" * 72)
    print(f"🚀 START grade01 step01 generate sample race html | date={date}")
    print("=" * 72)

    if not template_path.exists():
        raise FileNotFoundError(template_path)

    df = load_ticket_source(date)
    race_id = args.race_id or str(df["race_id"].iloc[0])
    race_df = df[df["race_id"].astype(str) == race_id].copy()

    if race_df.empty:
        raise ValueError(f"race_id not found in step43: {race_id}")

    race_meta = load_race_meta(date, race_id)
    odds_update_time = load_odds_update_time(date, race_id)
    arare_meta = load_arare_meta(date, race_id)
    result_payouts = load_result_payouts(date, race_id)
    racer_df = load_racer_stats_table(date, race_id)
    racer_html = build_racer_stats_html(racer_df)
    lineup_html = build_lineup_html(racer_df)
    odds_popularity_df = load_real_odds_popularity_source(date, race_id)
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

    output_html = replace_basic_text(template, race_id, race_meta, odds_update_time, arare_meta, date)
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_html, encoding="utf-8")

    print(f"📄 template: {template_path}")
    print(f"📄 source: {df.attrs.get('source_path', 'unknown')}")
    print(f"📊 race_id: {race_id}")
    class_name_log = str(race_meta.get("class_name", "")).strip()
    class_name_part = f"（{class_name_log}）" if class_name_log else ""
    print(f"📊 page_title: {race_meta.get('venue_name', '')} {race_meta.get('grade', '')} 第{int(race_meta.get('race_no', 0))}レース{class_name_part}")
    print(f"📊 cup_name: {race_meta.get('cup_name', '') or '--'}")
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
    if len(racer_df) == 0:
        print("⚠️ racer_stats not found for this race_id")
    print(f"📊 source rows: {len(race_df)}")
    print(f"📊 output top_exacta: {args.top_exacta}")
    print(f"📊 output top_trifecta: {args.top_trifecta}")
    print(f"📊 output top_trio: {args.top_trio}")
    print(f"💾 saved: {output_path}")
    print("=" * 72)
    print(f"🎉 END grade01 step01 generate sample race html | date={date}")
    print("=" * 72)


if __name__ == "__main__":
    main()