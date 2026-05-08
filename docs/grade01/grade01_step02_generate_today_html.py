#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step02_generate_today_html.py

目的:
step43 のCSVから当日のレース一覧ページ (today.html) を生成する（テンプレ方式）

入力:
data/sim06/step43/sim06_step43_all_top_tickets_YYYY-MM-DD.csv

出力:
docs/grade/today.html

重要:
- today_template.html はデザイン原本なので上書きしない
- today.html は出力用なので毎回上書きしてOK
- race-list の中身だけを差し替える
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd


DEFAULT_DATE = "2026-04-26"
TEMPLATE_PATH = Path("docs/grade/today_template.html")
OUTPUT_PATH = Path("docs/grade/today.html")

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
    return parser.parse_args()


def load_step43(date: str) -> pd.DataFrame:
    path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"step43 is empty: {path}")
    return df


def parse_race_id(race_id: str):
    # 例: 2026-04-26_42_04R
    parts = str(race_id).split("_")
    date = parts[0]
    venue_id = parts[1]
    race_no = parts[2].replace("R", "")
    return date, venue_id, race_no


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


def normalize_grade(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    upper = text.upper().replace("Ｇ", "G").replace("Ｆ", "F")
    return GRADE_SYMBOL_MAP.get(upper, text)


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


def load_entry_meta(date: str) -> pd.DataFrame:
    entry_path = find_entry_path(date)
    if entry_path is None:
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time", "venue_name", "grade", "class_name", "cup_name"])

    entry = pd.read_csv(entry_path)
    if entry.empty:
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time", "venue_name", "grade", "class_name", "cup_name"])

    venue_id_col = detect_column(entry, ["venue_id", "place_id", "jyocode", "jyo_code"])
    venue_name_col = detect_column(entry, ["venue_name", "place_name", "jyo_name", "競輪場", "場名"])
    race_col = detect_column(entry, ["race_no", "race_num", "race_number", "race"])
    time_col = detect_column(entry, ["post_time", "start_time", "race_time", "発走時間", "発走時刻", "締切時刻"])
    grade_col = detect_column(entry, ["race_grade", "grade", "grade_name", "グレード", "レースグレード"])
    class_name_col = detect_column(entry, ["class_name", "race_class", "race_class_name", "class", "レース種別", "競走種目"])
    cup_name_col = detect_column(entry, ["cup_name", "cup", "cup_title", "開催名"])
    date_col = detect_column(entry, ["date", "race_date"])

    if venue_id_col is None or race_col is None:
        return pd.DataFrame(columns=["date", "venue_id", "race_no", "post_time", "venue_name", "grade", "class_name", "cup_name"])

    cols = [venue_id_col, race_col]
    if time_col:
        cols.append(time_col)
    if venue_name_col:
        cols.append(venue_name_col)
    if grade_col:
        cols.append(grade_col)
    if class_name_col:
        cols.append(class_name_col)
    if cup_name_col:
        cols.append(cup_name_col)
    if date_col:
        cols.append(date_col)

    out = entry[cols].copy()
    out = out.rename(columns={venue_id_col: "venue_id", race_col: "race_no"})
    if time_col:
        out = out.rename(columns={time_col: "post_time"})
    else:
        out["post_time"] = ""
    if venue_name_col:
        out = out.rename(columns={venue_name_col: "venue_name"})
    else:
        out["venue_name"] = ""
    if grade_col:
        out = out.rename(columns={grade_col: "grade"})
    else:
        out["grade"] = ""
    if class_name_col:
        out = out.rename(columns={class_name_col: "class_name"})
    else:
        out["class_name"] = ""
    if cup_name_col:
        out = out.rename(columns={cup_name_col: "cup_name"})
    else:
        out["cup_name"] = ""
    if date_col:
        out = out.rename(columns={date_col: "date"})
    else:
        out["date"] = date

    out["date"] = out["date"].astype(str)
    out["venue_id"] = pd.to_numeric(out["venue_id"], errors="coerce")
    out["race_no"] = pd.to_numeric(out["race_no"], errors="coerce")
    out = out.dropna(subset=["venue_id", "race_no"])
    out["venue_id"] = out["venue_id"].astype(int)
    out["race_no"] = out["race_no"].astype(int)
    out["post_time"] = out["post_time"].map(normalize_time_text)
    out["grade"] = out["grade"].map(normalize_grade)
    out["class_name"] = out["class_name"].astype(str).replace({"nan": "", "None": ""}).str.strip()
    out["cup_name"] = out["cup_name"].astype(str).replace({"nan": "", "None": ""}).str.strip()
    out["venue_name"] = out.apply(
        lambda r: str(r["venue_name"]).strip() if str(r["venue_name"]).strip() else VENUE_NAME_MAP.get(int(r["venue_id"]), f"v{int(r['venue_id'])}"),
        axis=1,
    )

    return out[["date", "venue_id", "race_no", "post_time", "venue_name", "grade", "class_name", "cup_name"]].drop_duplicates(
        subset=["date", "venue_id", "race_no"],
        keep="last",
    )


# ========== Venue finish tactics summary ==========
def normalize_rank_for_tactics(value) -> int | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    m = re.search(r"\d+", text)
    if not m:
        return None
    return int(m.group(0))


def normalize_finish_tactic(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""

    # 表記ゆれを吸収
    if "逃" in text:
        return "逃"
    if "捲" in text or "まく" in text or "マク" in text:
        return "捲"
    if "差" in text:
        return "差"
    if text == "マ" or "マーク" in text:
        return "マ"
    return text

# --- 追加: グレードレース判定関数 ---
def is_grade_race_for_tactics(value) -> bool:
    """results側のグレード表記を、GP/G1/G2/G3相当かどうかで判定する。"""
    if pd.isna(value):
        return False
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return False

    upper = text.upper().replace("Ｇ", "G").replace("Ⅰ", "1").replace("Ⅱ", "2").replace("Ⅲ", "3")
    upper = upper.replace("Ｉ", "1").replace("II", "2").replace("III", "3")

    try:
        code = int(float(upper))
        return code in {0, 1, 2, 3}
    except Exception:
        pass

    return upper in {"GP", "G1", "G2", "G3"}


def find_result_path(date: str) -> Path | None:
    year = str(date)[:4]
    candidates = [
        Path(f"data/results/{year}/results_{date}.csv"),
        Path(f"data/results/results_{date}.csv"),
        Path(f"data/result/{year}/results_{date}.csv"),
        Path(f"data/result/results_{date}.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_venue_tactics_summary(date: str, venue_ids: list[str], lookback_days: int = 365) -> pd.DataFrame:
    """対象競輪場の過去1年・1着・2着決まり手をresultsから集計する（9車立グレードレース限定）。"""
    target_dt = pd.to_datetime(date)
    start_dt = target_dt - pd.Timedelta(days=lookback_days)
    end_dt = target_dt - pd.Timedelta(days=1)
    dates = pd.date_range(start_dt, end_dt, freq="D")
    target_venues = {int(v) for v in venue_ids}

    frames = []
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        path = find_result_path(d_str)
        if path is None:
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if df.empty:
            continue

        venue_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code", "vel_code"])
        rank_col = detect_column(df, ["rank", "finish_rank", "result_rank", "着", "着順"])
        tactic_col = detect_column(df, ["finish_tactics", "決まり手", "kimarite", "winning_tactic"])
        car_col = detect_column(df, ["car_no", "bike_no", "racer_no", "車番"])
        grade_col = detect_column(df, ["race_grade_id", "race_grade", "grade", "grade_name", "グレード", "レースグレード"])
        race_col = detect_column(df, ["race_no", "race_num", "race_number", "race"])

        # 9車立・グレードレース判定に必要な列がない場合は、その日付は集計対象外にする
        if car_col is None or grade_col is None or race_col is None:
            continue

        work = df[[venue_col, race_col, car_col, grade_col, rank_col, tactic_col]].copy()
        work = work.rename(
            columns={
                venue_col: "venue_id",
                race_col: "race_no",
                car_col: "car_no",
                grade_col: "grade_for_filter",
                rank_col: "rank",
                tactic_col: "finish_tactics",
            }
        )
        work["venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
        work = work.dropna(subset=["venue_id"])
        work["venue_id"] = work["venue_id"].astype(int)
        work = work[work["venue_id"].isin(target_venues)].copy()
        if work.empty:
            continue
        work["race_no"] = pd.to_numeric(work["race_no"], errors="coerce")
        work["car_no"] = pd.to_numeric(work["car_no"], errors="coerce")
        work = work.dropna(subset=["race_no", "car_no"])
        if work.empty:
            continue
        work["race_no"] = work["race_no"].astype(int)
        work["car_no"] = work["car_no"].astype(int)
        work["is_grade_race"] = work["grade_for_filter"].map(is_grade_race_for_tactics)

        # 9車立かつグレードレースのみ対象
        race_keys = ["venue_id", "race_no"]
        race_size = work.groupby(race_keys)["car_no"].transform("nunique")
        grade_ok = work.groupby(race_keys)["is_grade_race"].transform("max")
        work = work[(race_size == 9) & (grade_ok)].copy()
        if work.empty:
            continue

        work["rank_norm"] = work["rank"].map(normalize_rank_for_tactics)
        work["finish_tactics"] = work["finish_tactics"].map(normalize_finish_tactic)
        work = work[(work["rank_norm"].isin([1, 2])) & (work["finish_tactics"] != "")].copy()
        if not work.empty:
            frames.append(work[["venue_id", "finish_tactics", "rank_norm"]])

    if not frames:
        return pd.DataFrame(columns=["venue_id", "finish_tactics", "count_first", "rate_first", "count_second", "rate_second", "total_first", "total_second"])

    all_df = pd.concat(frames, ignore_index=True)
    # 1着・2着ごとに集計
    total_first = all_df[all_df["rank_norm"] == 1].groupby("venue_id").size().rename("total_first").reset_index()
    total_second = all_df[all_df["rank_norm"] == 2].groupby("venue_id").size().rename("total_second").reset_index()
    agg_first = all_df[all_df["rank_norm"] == 1].groupby(["venue_id", "finish_tactics"]).size().rename("count_first").reset_index()
    agg_second = all_df[all_df["rank_norm"] == 2].groupby(["venue_id", "finish_tactics"]).size().rename("count_second").reset_index()
    agg = pd.merge(agg_first, agg_second, on=["venue_id", "finish_tactics"], how="outer").fillna(0)
    agg = agg.merge(total_first, on="venue_id", how="left").merge(total_second, on="venue_id", how="left")
    agg["rate_first"] = agg["count_first"] / agg["total_first"]
    agg["rate_second"] = agg["count_second"] / agg["total_second"]
    # 欠損値補完
    agg = agg.fillna(0)
    # 並び順
    agg = agg.sort_values(["venue_id", "count_first", "count_second"], ascending=[True, False, False]).reset_index(drop=True)
    return agg


def build_venue_tactics_summary_html(summary: pd.DataFrame, entry_meta: pd.DataFrame, venue_ids: list[str], bank_meta: pd.DataFrame | None = None) -> str:
    if summary.empty:
        return ""

    blocks = []
    tactic_order = ["逃", "捲", "差", "マ"]
    for venue_id_text in venue_ids:
        venue_id = int(venue_id_text)
        sub = summary[summary["venue_id"] == venue_id].copy()
        if sub.empty:
            continue

        venue_name = VENUE_NAME_MAP.get(venue_id, f"v{venue_id}")
        if not entry_meta.empty:
            meta_sub = entry_meta[entry_meta["venue_id"] == venue_id]
            if not meta_sub.empty:
                candidate = str(meta_sub.iloc[0].get("venue_name", "")).strip()
                if candidate and candidate.lower() != "nan":
                    venue_name = candidate

        bank_html = build_bank_summary_table_html(bank_meta if bank_meta is not None else pd.DataFrame(), venue_id)

        rows = []
        total_first = int(sub["total_first"].max()) if "total_first" in sub.columns and not sub.empty else 0
        total_second = int(sub["total_second"].max()) if "total_second" in sub.columns and not sub.empty else 0
        for tactic in tactic_order:
            r = sub[sub["finish_tactics"] == tactic]
            if r.empty:
                count1 = 0
                rate1 = 0.0
                count2 = 0
                rate2 = 0.0
            else:
                count1 = int(r.iloc[0]["count_first"])
                rate1 = float(r.iloc[0]["rate_first"])
                count2 = int(r.iloc[0]["count_second"])
                rate2 = float(r.iloc[0]["rate_second"])
            rows.append(
                f"""
          <tr>
            <td style="font-weight:900; white-space:nowrap; text-align:center; background:#f8fafc;">{html.escape(tactic)}</td>
            <td style="text-align:center;">{count1}</td>
            <td style="text-align:center;">{rate1 * 100:.1f}%</td>
            <td style="text-align:center;">{count2}</td>
            <td style="text-align:center;">{rate2 * 100:.1f}%</td>
          </tr>"""
            )

        blocks.append(
            f"""
      <div style="min-width:240px; flex:1 1 360px;">
        <div style="font-weight:900; color:#1e3a8a; margin-bottom:10px; font-size:1.02rem;">{html.escape(venue_name)}競輪場</div>
        {bank_html}
        <div style="font-weight:900; color:#1e3a8a; margin-bottom:6px;">決まり手（グレードレース 過去1年）</div>
        <div style="overflow-x:auto;">
          <table style="width:100%; border-collapse:collapse; font-size:0.88rem; table-layout:fixed;">
            <thead>
              <tr>
                <th rowspan="2" style="width:60px; text-align:center; vertical-align:middle;">決まり手</th>
                <th colspan="2" style="text-align:center; background:#eef2ff; color:#1e3a8a;">1着</th>
                <th colspan="2" style="text-align:center; background:#f0fdf4; color:#166534;">2着</th>
              </tr>
              <tr>
                <th style="text-align:center; width:70px;">数</th>
                <th style="text-align:center; width:70px;">率</th>
                <th style="text-align:center; width:70px;">数</th>
                <th style="text-align:center; width:70px;">率</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
        </div>
      </div>"""
        )

    if not blocks:
        return ""

    return f"""
    <section class="summary-card">
      <h2>📊 競輪場データ</h2>
      <div style="display:flex; flex-wrap:wrap; gap:14px; align-items:flex-start;">
        {''.join(blocks)}
      </div>
    </section>
"""


def insert_after_summary_card(template: str, insert_html: str) -> str:
    if not insert_html:
        return template
    marker = "</section>\n\n    <section class=\"venue-card\">"
    if marker in template:
        return template.replace(marker, f"</section>\n\n{insert_html}\n    <section class=\"venue-card\">", 1)
    return template


# ========== Arare meta functions ==========
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


def empty_arare_meta() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "venue_id", "race_no", "arare_prob", "arare_index", "arare_level"])


def load_arare_meta(date: str) -> pd.DataFrame:
    arare_path = find_arare_path(date)
    if arare_path is None:
        return empty_arare_meta()

    arare = pd.read_csv(arare_path)
    if arare.empty:
        return empty_arare_meta()

    date_col = detect_column(arare, ["date", "race_date"])
    venue_col = detect_column(arare, ["venue_id", "place_id", "jyocode", "jyo_code"])
    race_col = detect_column(arare, ["race_no", "race_num", "race_number", "race"])
    race_id_col = detect_column(arare, ["race_id"])
    prob_col = detect_column(arare, ["arare_prob", "pred_arare_prob", "pred_prob", "probability", "prob_is_arare"])

    if prob_col is None:
        return empty_arare_meta()

    work = arare.copy()

    if venue_col is None or race_col is None:
        if race_id_col is None:
            return empty_arare_meta()
        parsed = work[race_id_col].astype(str).map(parse_race_id)
        work["date"] = parsed.map(lambda x: x[0])
        work["venue_id"] = parsed.map(lambda x: x[1])
        work["race_no"] = parsed.map(lambda x: x[2])
    else:
        if date_col:
            work["date"] = work[date_col].astype(str)
        else:
            work["date"] = date
        work["venue_id"] = work[venue_col]
        work["race_no"] = work[race_col]

    work["date"] = work["date"].astype(str)
    work = work[work["date"] == date].copy()
    work["venue_id"] = pd.to_numeric(work["venue_id"], errors="coerce")
    work["race_no"] = pd.to_numeric(work["race_no"], errors="coerce")
    work["arare_prob"] = pd.to_numeric(work[prob_col], errors="coerce")
    work = work.dropna(subset=["venue_id", "race_no", "arare_prob"])

    if work.empty:
        return empty_arare_meta()

    work["venue_id"] = work["venue_id"].astype(int)
    work["race_no"] = work["race_no"].astype(int)
    work["arare_index"] = (work["arare_prob"] * 100).round().astype(int)
    work["arare_level"] = "低"
    work.loc[work["arare_prob"] >= 0.30, "arare_level"] = "中"
    work.loc[work["arare_prob"] >= 0.50, "arare_level"] = "高"

    return work[["date", "venue_id", "race_no", "arare_prob", "arare_index", "arare_level"]].drop_duplicates(
        subset=["date", "venue_id", "race_no"],
        keep="last",
    )


def render_arare_badge(arare_index, arare_level) -> str:
    if pd.isna(arare_index) or pd.isna(arare_level):
        return '<span class="badge">荒れ度 --</span>'

    level = str(arare_level).strip()
    if level == "高":
        style = "background:#fee2e2; color:#991b1b;"
    elif level == "中":
        style = "background:#dcfce7; color:#166534;"
    else:
        style = "background:#dbeafe; color:#1e40af;"

    return f'<span class="badge" style="{style}">荒れ度 {int(arare_index)}</span>'


def find_odds_term_path(date: str) -> Path | None:
    candidates = [
        Path(f"data/grade01/step05/grade01_step05_odds_term_table_{date}.csv"),
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
    time_col = detect_column(df, ["fetched_at", "odds_update_time", "updated_at", "scraped_at"])

    if time_col is None:
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
    work["odds_update_time"] = work[time_col].astype(str).replace({"nan": "", "NaT": "", "None": ""})
    work["odds_update_time"] = work["odds_update_time"].str.strip()
    work = work.dropna(subset=["venue_id", "race_no"])

    if work.empty:
        return empty_odds_meta()

    work["venue_id"] = work["venue_id"].astype(int)
    work["race_no"] = work["race_no"].astype(int)
    work = work[work["odds_update_time"].astype(str).str.strip() != ""].copy()
    if work.empty:
        return empty_odds_meta()

    return work[["date", "venue_id", "race_no", "odds_update_time"]].drop_duplicates(
        subset=["date", "venue_id", "race_no"],
        keep="last",
    )


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
        style = "background:#dbeafe; color:#1e40af;"
    return f'<span class="badge waiting" style="{style}">{odds_status}</span>'


# New function for latest update time
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


def build_event_title(meta: pd.DataFrame, venue_ids: list[str]) -> str:
    titles = []
    for venue_id_text in venue_ids:
        venue_id = int(venue_id_text)
        sub = meta[meta["venue_id"] == venue_id] if not meta.empty else pd.DataFrame()
        venue_name = VENUE_NAME_MAP.get(venue_id, f"v{venue_id}")
        grade = ""
        cup_name = ""
        if not sub.empty:
            row = sub.iloc[0]
            venue_name = str(row.get("venue_name", venue_name)).strip() or venue_name
            grade = str(row.get("grade", "")).strip()
            cup_name = str(row.get("cup_name", "")).strip()
        titles.append(" ".join([x for x in [venue_name, grade, cup_name] if x and x.lower() != "nan"]))
    return " / ".join(titles)


def build_rows(
    df: pd.DataFrame,
    entry_meta: pd.DataFrame,
    arare_meta: pd.DataFrame,
    odds_meta: pd.DataFrame,
    active_venue_id: int | None,
    active_race_no: int | None,
) -> str:
    race_ids = sorted(df["race_id"].astype(str).unique())

    rows = []
    for race_id in race_ids:
        _, venue_id, race_no = parse_race_id(race_id)
        venue_id_int = int(venue_id)
        race_no_int = int(race_no)
        link = f"./races/v{venue_id}/r{race_no}.html"

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

        arare_badge = render_arare_badge(pd.NA, pd.NA)
        if not arare_meta.empty:
            arare_sub = arare_meta[(arare_meta["venue_id"] == venue_id_int) & (arare_meta["race_no"] == race_no_int)]
            if not arare_sub.empty:
                arare_row = arare_sub.iloc[0]
                arare_badge = render_arare_badge(
                    arare_row.get("arare_index", pd.NA),
                    arare_row.get("arare_level", pd.NA),
                )

        odds_update_time = ""
        if not odds_meta.empty:
            odds_sub = odds_meta[(odds_meta["venue_id"] == venue_id_int) & (odds_meta["race_no"] == race_no_int)]
            if not odds_sub.empty:
                odds_update_time = str(odds_sub.iloc[0].get("odds_update_time", "")).strip()
        odds_status = calc_odds_status(parse_race_id(race_id)[0], post_time, odds_update_time)
        odds_badge = render_odds_badge(odds_status)

        race_label = f"{race_no}R{class_name_html}"
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
            race_label = (
                f'<span style="display:inline-flex; align-items:center; padding:4px 9px; '
                f'border-radius:999px; background:#fee2e2; color:#b91c1c; '
                f'border:1px solid #fecaca; font-weight:900; box-shadow:0 0 0 2px rgba(220,38,38,0.08); '
                f'white-space:nowrap;">{race_label}</span>'
            )

        rows.append(
            f"""
        <div class="{row_class}"{row_style}>
          <div class="race-no">{race_label}</div>
          <div>
            <div>
              {arare_badge}
              {odds_badge}
            </div>
            <div class="race-meta">発走予定 {post_time}</div>
          </div>
          <a class="race-link" href="{link}">買い目を見る</a>
        </div>"""
        )

    return "\n".join(rows)


def replace_race_list(template: str, rows_html: str) -> str:
    """<div class="race-list"> の中身だけを差し替える。"""
    pattern = re.compile(
        r'(<div class="race-list">)(.*?)(\n\s*</div>\s*</section>)',
        flags=re.DOTALL,
    )
    replacement = rf'\1\n{rows_html}\n      \3'

    new_html, count = pattern.subn(replacement, template, count=1)
    if count != 1:
        raise ValueError('target <div class="race-list"> block not found in template')
    return new_html


def update_summary_values(template: str, date: str, df: pd.DataFrame, entry_meta: pd.DataFrame, odds_meta: pd.DataFrame) -> str:
    race_ids = df["race_id"].astype(str).unique()
    venue_ids = sorted({parse_race_id(race_id)[1] for race_id in race_ids})
    event_title = build_event_title(entry_meta, venue_ids)

    out = template.replace("YYYY-MM-DD", date)
    out = out.replace('<div class="value">0</div>', f'<div class="value">{len(venue_ids)}</div>', 1)
    out = out.replace('<div class="value">0R</div>', f'<div class="value">{len(race_ids)}R</div>', 1)
    out = out.replace('<div class="label">最終更新</div>\n          <div class="value">--:--</div>', f'<div class="label">最終更新</div>\n          <div class="value">{latest_update_text(odds_meta)}</div>')

    if event_title:
        out = out.replace(
            "<h2>📅 本日のグレードレース</h2>",
            f'<h2>📅 本日のグレードレース <span style="display:inline-block; margin-left:8px; padding:4px 10px; border-radius:999px; background:#fee2e2; color:#991b1b; font-weight:900;">{event_title}</span></h2>',
        )
        out = out.replace("<h2>サンプル競輪場</h2>", f"<h2>{event_title}</h2>")

    return out


def main():
    args = parse_args()
    date = args.date

    print("=" * 72)
    print(f"🚀 START grade01 step02 generate today html | date={date}")
    print("=" * 72)

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(TEMPLATE_PATH)

    df = load_step43(date)
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Patch CSS for .race-row and .race-no (layout fix)
    # Update .race-row grid-template-columns from 80px to 120px
    template = re.sub(
        r'(\.race-row\s*\{\s*display:\s*grid;\s*grid-template-columns:\s*)80px(\s+1fr\s+auto;)',
        r'\g<1>120px\2',
        template,
        flags=re.MULTILINE
    )
    # Add white-space:nowrap to .race-no
    template = re.sub(
        r'(\.race-no\s*\{\s*[^}]*?)\}',
        lambda m: m.group(1) + ("\n  white-space: nowrap;" if "white-space" not in m.group(1) else "") + "\n}",
        template,
        count=1,
        flags=re.MULTILINE
    )

    entry_meta = load_entry_meta(date)
    arare_meta = load_arare_meta(date)
    odds_meta = load_odds_meta(date)

    race_ids = df["race_id"].astype(str).unique()
    venue_ids = sorted({parse_race_id(race_id)[1] for race_id in race_ids})
    tactics_summary = load_venue_tactics_summary(date, venue_ids)
    bank_meta = load_venue_bank_master()
    tactics_summary_html = build_venue_tactics_summary_html(tactics_summary, entry_meta, venue_ids, bank_meta)

    # --- determine active race (next race after latest odds trigger) ---
    active_venue_id = None
    active_race_no = None
    try:
        term_path = Path(f"data/grade01/step05/grade01_step05_odds_term_table_{date}.csv")
        if term_path.exists():
            term_df = pd.read_csv(term_path)
            term_df["odds_fetch_time"] = term_df["odds_fetch_time"].astype(str)

            now_dt = pd.Timestamp.now()
            term_df["odds_dt"] = pd.to_datetime(
                term_df["date"].astype(str) + " " + term_df["odds_fetch_time"],
                errors="coerce"
            )

            done = term_df[term_df["odds_dt"] <= now_dt]
            if not done.empty:
                latest = done.sort_values(["venue_id", "race_no"]).iloc[-1]
                active_venue_id = int(latest["venue_id"])
                active_race_no = int(latest["race_no"])
    except Exception:
        active_venue_id = None
        active_race_no = None

    rows_html = build_rows(df, entry_meta, arare_meta, odds_meta, active_venue_id, active_race_no)
    html = update_summary_values(template, date, df, entry_meta, odds_meta)
    html = insert_after_summary_card(html, tactics_summary_html)
    html = replace_race_list(html, rows_html)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")

    print(f"📄 template: {TEMPLATE_PATH}")
    print(f"📊 races: {df['race_id'].nunique()}")
    print(f"📊 entry_meta rows: {len(entry_meta)}")
    if "cup_name" in entry_meta.columns:
        print(f"📊 entry_meta cup_name rows: {entry_meta['cup_name'].astype(str).str.strip().ne('').sum()}")
    print(f"📊 arare_meta rows: {len(arare_meta)}")
    print(f"📊 odds_meta rows: {len(odds_meta)}")
    print(f"📊 tactics_summary rows: {len(tactics_summary)}")
    print(f"📊 bank_meta rows: {len(bank_meta)}")
    print(f"💾 saved: {OUTPUT_PATH}")
    print("=" * 72)
    print(f"🎉 END grade01 step02 generate today html | date={date}")
    print("=" * 72)



# ========== Venue master / bank summary ==========
def find_venue_master_path() -> Path | None:
    candidates = [
        Path("data/master/venue_master.csv"),
        Path("data/masters/venue_master.csv"),
        Path("data/venue_master.csv"),
        Path("venue_master.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_venue_bank_master() -> pd.DataFrame:
    path = find_venue_master_path()
    columns = ["venue_id", "venue_name", "track_length_m", "virtual_straight_m", "banking_angle"]
    if path is None:
        return pd.DataFrame(columns=columns)

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=columns)

    venue_id_col = detect_column(df, ["venue_id", "place_id", "jyocode", "jyo_code", "vel_code"])
    venue_name_col = detect_column(df, ["venue_name", "place_name", "jyo_name", "競輪場", "場名"])
    track_col = detect_column(df, ["track_length_m", "track_length", "周長"])
    straight_col = detect_column(df, ["virtual_straight_m", "virtual_straight", "みなし直線"])
    cant_col = detect_column(df, ["banking_angle", "banking", "cant", "カント"])

    if venue_id_col is None:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["venue_id"] = pd.to_numeric(work[venue_id_col], errors="coerce")
    work = work.dropna(subset=["venue_id"])
    work["venue_id"] = work["venue_id"].astype(int)

    if venue_name_col:
        work["venue_name"] = work[venue_name_col].astype(str).replace({"nan": "", "None": ""}).str.strip()
    else:
        work["venue_name"] = work["venue_id"].map(lambda x: VENUE_NAME_MAP.get(int(x), f"v{int(x)}"))

    if track_col:
        work["track_length_m"] = pd.to_numeric(work[track_col].astype(str).str.replace("m", "", regex=False), errors="coerce")
    else:
        work["track_length_m"] = pd.NA

    if straight_col:
        work["virtual_straight_m"] = pd.to_numeric(work[straight_col].astype(str).str.replace("m", "", regex=False), errors="coerce")
    else:
        work["virtual_straight_m"] = pd.NA

    if cant_col:
        work["banking_angle"] = pd.to_numeric(
            work[cant_col].astype(str).str.replace("°", "", regex=False),
            errors="coerce",
        )
    else:
        work["banking_angle"] = pd.NA

    return work[columns].drop_duplicates(subset=["venue_id"], keep="last")


def fmt_m(value) -> str:
    if pd.isna(value):
        return "--"
    value = float(value)
    if value.is_integer():
        return f"{int(value)}m"
    return f"{value:.1f}m"


def fmt_degree(value) -> str:
    if pd.isna(value):
        return "--"
    return f"{float(value):.2f}°"


def build_bank_summary_table_html(bank_meta: pd.DataFrame, venue_id: int) -> str:
    if bank_meta.empty:
        return ""

    sub = bank_meta[bank_meta["venue_id"] == int(venue_id)]
    if sub.empty:
        return ""

    row = sub.iloc[0]
    track_length = row.get("track_length_m", pd.NA)
    if pd.isna(track_length):
        avg_sub = pd.DataFrame()
        avg_label = "同周長平均"
    else:
        track_length_int = int(float(track_length))
        track_series = pd.to_numeric(bank_meta["track_length_m"], errors="coerce")
        if track_length_int in {333, 335}:
            avg_sub = bank_meta[track_series.isin([333, 335])]
            avg_label = "333m平均"
        else:
            avg_sub = bank_meta[track_series == track_length_int]
            avg_label = f"{track_length_int}m平均"

    avg_straight = avg_sub["virtual_straight_m"].mean() if not avg_sub.empty else pd.NA
    avg_cant = avg_sub["banking_angle"].mean() if not avg_sub.empty else pd.NA

    rows = [
        ("周長", fmt_m(row.get("track_length_m", pd.NA)), "-"),
        ("みなし直線", fmt_m(row.get("virtual_straight_m", pd.NA)), fmt_m(avg_straight)),
        ("カント", fmt_degree(row.get("banking_angle", pd.NA)), fmt_degree(avg_cant)),
    ]

    rows_html = "".join(
        f"""
          <tr>
            <td style="font-weight:900; white-space:nowrap; text-align:center; background:#f8fafc;">{html.escape(label)}</td>
            <td style="text-align:center; font-weight:800;">{html.escape(value)}</td>
            <td style="text-align:center; color:#4b5563;">{html.escape(avg)}</td>
          </tr>"""
        for label, value, avg in rows
    )

    return f"""
        <div style="font-weight:900; color:#1e3a8a; margin:0 0 6px;">バンクデータ</div>
        <div style="overflow-x:auto; margin-bottom:14px;">
          <table style="width:100%; border-collapse:collapse; font-size:0.88rem; table-layout:fixed;">
            <thead>
              <tr>
                <th style="width:88px; text-align:center; background:#f8fafc;">項目</th>
                <th style="text-align:center; background:#eef2ff; color:#1e3a8a;">当場</th>
                <th style="text-align:center; background:#f0fdf4; color:#166534;">{html.escape(avg_label)}</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>"""


if __name__ == "__main__":
    main()