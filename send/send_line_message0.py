import argparse
import datetime
import os
import re
from pathlib import Path
import sys

import pandas as pd
import pytz
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.public01.car9.common.utils import load_entry_meta


# ============================================================
# args
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--dryrun",
    action="store_true",
    help="LINEには送らず、printだけする",
)

args = parser.parse_args()


# ============================================================
# LINE
# ============================================================

def should_send_today():
    return True


ACCESS_TOKEN = os.environ.get("LINE_TOKEN")

USER_IDS = [
    x.strip()
    for x in os.environ.get(
        "LINE_USER_IDS",
        "",
    ).split(";")
    if x.strip()
]

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


# ============================================================
# date
# ============================================================

jst = datetime.datetime.now(
    pytz.timezone("Asia/Tokyo")
)

today_str = jst.strftime("%Y-%m-%d")


# ============================================================
# bet01
# ============================================================

# ============================================================
# LINE予想元
#
# 正式移行前 : sim06
# 正式移行後 : bet01
#
# public01 / bet01へ正式移行したら、
# PREDICTION_SOURCE = "bet01"
# に変更するだけで切替可能。
# ============================================================

PREDICTION_SOURCE = "sim06"

if PREDICTION_SOURCE == "sim06":
    LINE_STEP43 = Path(
        "data/sim06/step43"
    ) / (
        f"sim06_step43_all_top_tickets_"
        f"{today_str}.csv"
    )

elif PREDICTION_SOURCE == "bet01":
    LINE_STEP43 = Path(
        "data/bet01/car9/step43"
    ) / (
        f"bet01_car9_step43_all_top_tickets_"
        f"{today_str}.csv"
    )

else:
    raise ValueError(
        f"unknown PREDICTION_SOURCE: "
        f"{PREDICTION_SOURCE}"
    )

TOP_N = 3

TICKET_LABELS = {
    "exacta": "2車単",
    "trifecta": "3連単",
    "trio": "3連複",
}


# ============================================================
# helpers
# ============================================================

def normalize_name(value) -> str:
    if pd.isna(value):
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def normalize_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def get_probability_pct(
    df: pd.DataFrame,
) -> pd.Series:

    if "probability_pct" in df.columns:
        return pd.to_numeric(
            df["probability_pct"],
            errors="coerce",
        )

    if "probability" in df.columns:
        prob = pd.to_numeric(
            df["probability"],
            errors="coerce",
        )

        valid = prob.dropna()

        if valid.empty:
            return prob

        # 0～1なら％へ変換
        if valid.max() <= 1.0:
            return prob * 100.0

        return prob

    raise ValueError(
        "probability_pct / probability "
        "column not found"
    )


def load_racer_name_map(
    ticket_df: pd.DataFrame,
) -> dict:

    required = {
        "venue_id",
        "race_no",
        "car_no",
        "name_kanji",
    }

    # --------------------------------------------------------
    # Step43自身に選手名があればそれを使用
    # --------------------------------------------------------

    if required.issubset(
        ticket_df.columns
    ):
        source_df = ticket_df.copy()

    else:
        source_df = None

        # ----------------------------------------------------
        # bet01/car9 内から当日データを探す
        # Step12など選手情報を持つCSVを優先
        # ----------------------------------------------------

        candidates = []

        bet_root = Path(
            "data/bet01/car9"
        )

        if bet_root.exists():
            candidates.extend(
                sorted(
                    bet_root.rglob(
                        f"*{today_str}*.csv"
                    )
                )
            )

        for path in candidates:
            try:
                tmp = pd.read_csv(
                    path,
                    low_memory=False,
                )
            except Exception:
                continue

            if required.issubset(
                tmp.columns
            ):
                source_df = tmp
                print(
                    "✅ 選手名source:",
                    path,
                )
                break

        # ----------------------------------------------------
        # 旧LINE用ファイルを最後のfallbackとして使用
        # 選手名だけ利用し、予想には使わない
        # ----------------------------------------------------

        if source_df is None:
            legacy = Path(
                "docs/predict/csv/gr01"
            ) / (
                f"final_prediction_v2_"
                f"{today_str}.csv"
            )

            if legacy.exists():
                try:
                    tmp = pd.read_csv(
                        legacy,
                        low_memory=False,
                    )

                    if required.issubset(
                        tmp.columns
                    ):
                        source_df = tmp
                        print(
                            "ℹ️ 選手名source fallback:",
                            legacy,
                        )
                except Exception:
                    pass

    if source_df is None:
        print(
            "⚠️ 選手名sourceが見つかりません。"
            "車番のみ表示します。"
        )
        return {}

    name_map = {}

    for _, row in source_df.iterrows():

        venue_id = normalize_int(
            row.get("venue_id")
        )

        race_no = normalize_int(
            row.get("race_no")
        )

        car_no = normalize_int(
            row.get("car_no")
        )

        if (
            venue_id is None
            or race_no is None
            or car_no is None
        ):
            continue

        name = normalize_name(
            row.get("name_kanji")
        )

        if not name:
            continue

        name_map[
            (
                venue_id,
                race_no,
                car_no,
            )
        ] = name

    print(
        "✅ 選手名map:",
        len(name_map),
        "件",
    )

    return name_map


def venue_display(
    row: pd.Series,
) -> str:

    for col in [
        "venue_name",
        "venue",
    ]:
        if col not in row.index:
            continue

        value = row.get(col)

        if (
            pd.notna(value)
            and str(value).strip()
        ):
            return str(value).strip()

    venue_id = normalize_int(
        row.get("venue_id")
    )

    if venue_id is not None:
        return f"場ID{venue_id}"

    return "会場不明"



def event_display_names(
    date: str,
    ticket_df: pd.DataFrame,
) -> list[str]:
    """
    WEB側と同じentryメタ情報から
    LINE用開催名を作る。

    例:
    前橋 GⅢ 三山王冠争奪戦（3日目）
    """
    entry_meta = load_entry_meta(date)

    if entry_meta.empty:
        return []

    target_venue_ids = {
        normalize_int(value)
        for value in ticket_df["venue_id"].dropna()
    }

    target_venue_ids.discard(None)

    if target_venue_ids:
        entry_meta = entry_meta.loc[
            entry_meta["venue_id"].isin(
                target_venue_ids
            )
        ].copy()

    event_names = []

    for _, group in entry_meta.groupby(
        "venue_id",
        sort=False,
    ):
        row = group.iloc[0]

        venue_name = str(
            row.get("venue_name", "")
        ).strip()

        grade = str(
            row.get("grade", "")
        ).strip()

        cup_name = str(
            row.get("cup_name", "")
        ).strip()

        cup_day = str(
            row.get("cup_day", "")
        ).strip()

        parts = [
            value
            for value in [
                venue_name,
                grade,
                cup_name,
            ]
            if value
            and value.lower() != "nan"
        ]

        event_text = " ".join(
            parts
        ).strip()

        if (
            cup_day
            and cup_day.lower() != "nan"
        ):
            if not (
                cup_day.startswith("（")
                and cup_day.endswith("）")
            ):
                cup_day = f"（{cup_day}）"

            event_text = (
                f"{event_text}{cup_day}"
            ).strip()

        if (
            event_text
            and event_text not in event_names
        ):
            event_names.append(
                event_text
            )

    return event_names

def make_racer_line(
    row: pd.Series,
    racer_name_map: dict,
) -> str:

    venue_id = normalize_int(
        row.get("venue_id")
    )

    race_no = normalize_int(
        row.get("race_no")
    )

    if (
        venue_id is None
        or race_no is None
    ):
        return ""

    ticket_key = str(
        row.get(
            "ticket_key",
            "",
        )
    ).strip()

    car_numbers = []

    for part in ticket_key.split("-"):

        car_no = normalize_int(part)

        if car_no is not None:
            car_numbers.append(
                car_no
            )

    if not car_numbers:
        return ""

    displays = []

    for car_no in car_numbers:

        name = racer_name_map.get(
            (
                venue_id,
                race_no,
                car_no,
            ),
            "",
        )

        if name:
            displays.append(
                f"{car_no} {name}"
            )
        else:
            displays.append(
                str(car_no)
            )

    ticket_type = str(
        row.get(
            "ticket_type",
            "",
        )
    ).strip()

    # 2車単は横並び
    if ticket_type == "exacta":
        return (
            "   "
            + " - ".join(displays)
        )

    # 3連単・3連複は縦並び
    if ticket_type in {
        "trifecta",
        "trio",
    }:
        return "\n".join(
            f"   {display}"
            for display in displays
        )

    return (
        "   "
        + " - ".join(displays)
    )


# ============================================================
# message
# ============================================================

def build_message(
    df: pd.DataFrame,
) -> str:

    # ========================================================
    # source column normalization
    #
    # sim06 : race_num
    # bet01 : race_no
    #
    # LINE内部では race_no に統一する。
    # ========================================================

    df = df.copy()

    if (
        "race_no" not in df.columns
        and "race_num" in df.columns
    ):
        df = df.rename(
            columns={
                "race_num": "race_no",
            }
        )


    required = {
        "ticket_type",
        "ticket_key",
        "venue_id",
        "race_no",
    }

    missing = sorted(
        required - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"{PREDICTION_SOURCE} Step43 required "
            f"columns missing: {missing}"
        )

    work = df.copy()

    work[
        "_probability_pct"
    ] = get_probability_pct(
        work
    )

    racer_name_map = (
        load_racer_name_map(
            work
        )
    )

    event_names = event_display_names(
        today_str,
        work,
    )

    lines = [
        f"【{today_str} 競輪AI 高確率買い目】",
        "",
    ]

    if event_names:
        for event_name in event_names:
            lines.append(
                f"開催：{event_name}"
            )
    else:
        lines.append(
            "開催：開催情報なし"
        )

    for (
        ticket_type,
        ticket_label,
    ) in TICKET_LABELS.items():

        sub = work.loc[
            work[
                "ticket_type"
            ].astype(str).eq(
                ticket_type
            )
        ].copy()

        sub = sub.loc[
            sub[
                "_probability_pct"
            ].notna()
        ].copy()

        # ----------------------------------------------------
        # その日の全レース・全買い目を横断して
        # 純粋に確率TOP3
        # ----------------------------------------------------

        sub = (
            sub
            .sort_values(
                "_probability_pct",
                ascending=False,
            )
            .head(TOP_N)
        )

        lines.extend(
            [
                "",
                f"■ {ticket_label} TOP{TOP_N}",
            ]
        )

        if sub.empty:
            lines.append(
                "該当買い目なし"
            )
            continue

        for rank, (_, row) in enumerate(
            sub.iterrows(),
            start=1,
        ):

            venue = venue_display(
                row
            )

            race_no = normalize_int(
                row.get("race_no")
            )

            if race_no is None:
                race_no = row.get(
                    "race_no",
                    "?",
                )

            ticket_key = str(
                row.get(
                    "ticket_key",
                    "",
                )
            ).strip()

            probability = float(
                row[
                    "_probability_pct"
                ]
            )

            lines.append(
                f"{rank}. "
                f"{venue} "
                f"{race_no}R "
                f"{ticket_key}  "
                f"{probability:.2f}%"
            )

            racer_line = (
                make_racer_line(
                    row,
                    racer_name_map,
                )
            )

            if racer_line:
                lines.append(
                    racer_line
                )

    detail_url = (
        "https://kazuhikosatomi.github.io/"
        "Keirin_ai_web/"
    )

    lines.extend(
        [
            "",
            f"🔗 詳細：{detail_url}",
        ]
    )

    return "\n".join(lines)


def has_car9_races(date: str) -> bool:
    """当日のentryメタ情報に9車レースが1つでもあるか確認する。"""
    entry_meta = load_entry_meta(date)

    if entry_meta.empty:
        return False

    required = {"venue_id", "race_no"}

    if not required.issubset(entry_meta.columns):
        return False

    race_sizes = (
        entry_meta
        .dropna(subset=["venue_id", "race_no"])
        .groupby(["venue_id", "race_no"])
        .size()
    )

    return bool((race_sizes == 9).any())


# ============================================================
# main
# ============================================================

if LINE_STEP43.exists():

    df = pd.read_csv(
        LINE_STEP43,
        low_memory=False,
    )

    message_text = (
        build_message(df)
    )

    print(
        f"✅ LINE prediction source: {PREDICTION_SOURCE}",
        LINE_STEP43,
    )

    print(
        "✅ 2車単・3連単・3連複の"
        f"全レース横断TOP{TOP_N}"
        "を作成しました。"
    )

else:

    if not has_car9_races(today_str):
        print(
            f"ℹ️ {today_str}: 9車レースなし。"
            "LINE送信をスキップします。"
        )
        raise SystemExit(0)

    message_text = (
        f"{today_str} の"
        f"{PREDICTION_SOURCE} Step43予測結果が"
        "見つかりませんでした。"
    )

    print(message_text)


print()
print("📨 送信メッセージ:")
print(message_text)


# ============================================================
# dryrun
# ============================================================

if args.dryrun:

    print()
    print(
        "🚫 LINE送信はスキップされました "
        "(--dryrun 指定)"
    )

    raise SystemExit(0)


# ============================================================
# LINE push
# ============================================================

message = {
    "type": "text",
    "text": message_text,
}


if should_send_today():

    print()
    print(
        "📦 メッセージ内容:\n"
        + message_text
    )

    if not ACCESS_TOKEN:
        raise RuntimeError(
            "LINE_TOKEN が"
            "設定されていません。"
        )

    if not USER_IDS:
        raise RuntimeError(
            "LINE_USER_IDS が"
            "設定されていません。"
        )

    for user_id in USER_IDS:

        payload = {
            "to": user_id,
            "messages": [
                message
            ],
        }

        res = requests.post(
            "https://api.line.me/"
            "v2/bot/message/push",
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(
            f"📤 To {user_id} "
            f"=> Status: "
            f"{res.status_code}, "
            f"Response: "
            f"{res.text}"
        )

else:
    print(
        "⏸ LINE送信スキップ"
    )
