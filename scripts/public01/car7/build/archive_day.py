#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
archive_day.py

目的:
docs/public/latest/car7/ を日付別car7アーカイブへコピーする。

入力:
docs/public/latest/car7/

出力:
docs/public/archive/car7/YYYY-MM-DD/

重要:
- snapshot は開催中更新用
- final はarchive保存用
- archive は保存用
- 既存 archive がある場合は、--force 指定時だけ上書きする
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.public01.car7.common.config import TOP_PAGE_URL


DEFAULT_DATE = "2026-04-26"
LATEST_DIR = Path("docs/public/latest/car7")
ARCHIVE_ROOT = Path("docs/public/archive/car7")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE, help="対象日 YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="既存archiveを削除して作り直す")
    parser.add_argument(
        "--tmp",
        action="store_true",
        help="tmp/public01/car7 の latest/final → archive/YYYY-MM-DD を使用する",
    )
    return parser.parse_args()


def fix_archive_venue_index_links(archive_day_dir: Path) -> None:
    """archive/YYYY-MM-DD/vXX/index.html の戻り先を archive/index.html へ補正する。"""
    for path in sorted(archive_day_dir.glob("v*/index.html")):
        html = path.read_text(encoding="utf-8")

        replacements = {
            '<a href="../../../../index_grade05.html">← トップへ戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../../index.html">← 一覧へ戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../../index.html">← トップページへ戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../../index.html">← トップページに戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../index.html">← 一覧へ戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../index.html">← トップページへ戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
            '<a href="../../../index.html">← トップページに戻る</a>': '<a href="{top_href}">← 一覧へ戻る</a>',
        }

        before = html
        top_href = "../../index.html"
        for old, new in replacements.items():
            html = html.replace(old, new.format(top_href=top_href))

        if html != before:
            path.write_text(html, encoding="utf-8")
            print(f"🔗 fixed archive venue nav: {path}")
        else:
            print(f"🔗 archive venue nav unchanged: {path}")



def fix_archive_race_page_links(archive_day_dir: Path) -> None:
    """archive/YYYY-MM-DD/vXX/races/rYY.html の戻り先を vXX/index.html へ補正する。"""
    for path in sorted(archive_day_dir.glob("v*/races/r*.html")):
        html = path.read_text(encoding="utf-8")

        replacements = {
            '<a href="../../../../index.html">← 一覧へ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../../../../index.html">← トップページへ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../../../index.html">← 一覧へ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../../../index.html">← トップページへ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../../index.html">← 一覧へ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../../index.html">← トップページへ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../index.html">← 一覧へ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../index.html">← トップページへ戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
            '<a href="../index.html">← 一覧に戻る</a>': '<a href="../index.html">← 一覧へ戻る</a>',
        }

        before = html
        for old, new in replacements.items():
            html = html.replace(old, new)

        if html != before:
            path.write_text(html, encoding="utf-8")
            print(f"🔗 fixed archive race nav: {path}")
        else:
            print(f"🔗 archive race nav unchanged: {path}")


def main():
    args = parse_args()
    date = args.date

    if args.tmp:
        src = Path("tmp/public01/car7/latest/final")
        archive_root = Path("tmp/public01/car7/archive")
        print("🧪 archive mode: TMP")
    else:
        src = LATEST_DIR
        archive_root = ARCHIVE_ROOT
        print("🚀 archive mode: PUBLIC")

    dst = archive_root / date

    print("=" * 72)
    print(f"🚀 START public01 car7 archive day | date={date}")
    print("=" * 72)

    if not src.exists():
        raise FileNotFoundError(f"latest not found: {src}")

        return

    # archive元のlatestが、本当に指定日のデータか確認する。
    # 古いlatestを別日名のarchiveとして保存する事故を防ぐ。
    latest_json = src / "latest.json"

    if not latest_json.exists():
        raise RuntimeError(
            f"archive safety check failed: latest.json not found: {latest_json}"
        )

    try:
        latest_data = json.loads(latest_json.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"archive safety check failed: invalid latest.json: {latest_json}"
        ) from exc

    latest_date = latest_data.get("date") if isinstance(latest_data, dict) else None

    if not latest_date:
        raise RuntimeError(
            f"archive safety check failed: date missing in latest.json: {latest_json}"
        )

    if latest_date != date:
        raise RuntimeError(
            "archive safety check failed: "
            f"requested={date} latest={latest_date} source={src}"
        )

    print(f"✅ archive date check OK | requested={date} | latest={latest_date}")

    if dst.exists():
        if not args.force:
            raise FileExistsError(f"archive already exists: {dst}  ※上書きする場合は --force")
        shutil.rmtree(dst)

    # 公開archive対象:
    #   1) WATCH対象会場
    #   2) 全Rについて status / odds_status / result_status が
    #      すべて done になったOTHER会場
    watch_path = (
        Path("data/public01/car7/config")
        / f"watch_targets_{date}.csv"
    )
    term_path = (
        Path("data/public01/car7/watch")
        / f"public01_car7_odds_term_table_{date}.csv"
    )

    # WATCH対象が0場の日は watch_targets 自体が存在しない。
    # その場合は空集合として扱う。
    watch_venue_ids = set()

    if watch_path.exists():
        watch_df = pd.read_csv(watch_path, dtype=str).fillna("")

        if "venue_id" not in watch_df.columns:
            raise ValueError(f"watch targets missing venue_id: {watch_path}")

        watch_venue_ids = {
            int(float(str(value).strip()))
            for value in watch_df["venue_id"]
            if str(value).strip()
        }
    else:
        print(f"ℹ️ WATCH venues: none ({watch_path.name} not found)")

    completed_other_venue_ids = set()

    if term_path.exists():
        term_df = pd.read_csv(term_path, dtype=str).fillna("")

        required = {"venue_id", "status", "odds_status"}
        missing = required - set(term_df.columns)

        if missing:
            raise ValueError(
                f"term table missing columns: {sorted(missing)} | {term_path}"
            )

        # result_status は結果処理開始時に動的追加される。
        # まだ無い場合は全R未完了として扱う。
        if "result_status" not in term_df.columns:
            term_df["result_status"] = "pending"

        term_df["_venue_id"] = pd.to_numeric(
            term_df["venue_id"], errors="coerce"
        )
        term_df = term_df[term_df["_venue_id"].notna()].copy()
        term_df["_venue_id"] = term_df["_venue_id"].astype(int)

        other_df = term_df[
            ~term_df["_venue_id"].isin(watch_venue_ids)
        ].copy()

        for venue_id, group in other_df.groupby("_venue_id"):
            all_done = (
                group["status"].astype(str).eq("done")
                & group["odds_status"].astype(str).eq("done")
                & group["result_status"].astype(str).eq("done")
            ).all()

            if all_done:
                completed_other_venue_ids.add(int(venue_id))

    archive_venue_ids = watch_venue_ids | completed_other_venue_ids

    if not archive_venue_ids:
        raise ValueError(
            f"archive target venue is empty: date={date}"
        )

    print(f"🎯 archive WATCH venues: {sorted(watch_venue_ids)}")
    print(
        "✅ archive completed OTHER venues: "
        f"{sorted(completed_other_venue_ids)}"
    )
    print(f"📦 archive target venues: {sorted(archive_venue_ids)}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.mkdir(parents=True, exist_ok=False)

    # WATCH + 完了済みOTHERだけコピーする。
    copied_venues = []
    for venue_id in sorted(archive_venue_ids):
        venue_name = f"v{venue_id}"
        venue_src = src / venue_name
        venue_dst = dst / venue_name

        if not venue_src.exists():
            raise FileNotFoundError(
                f"watch target venue not found in latest: {venue_src}"
            )

        shutil.copytree(venue_src, venue_dst)
        copied_venues.append(venue_name)

    # latest.json も公開archive対象だけに絞る。
    archive_latest_data = dict(latest_data)

    items = archive_latest_data.get("items")
    if isinstance(items, list):
        filtered_items = []
        for item in items:
            if not isinstance(item, dict):
                continue

            raw_venue_id = item.get("venue_id", "")
            try:
                venue_id = int(float(str(raw_venue_id).lstrip("vV")))
            except (TypeError, ValueError):
                continue

            if venue_id in archive_venue_ids:
                filtered_items.append(item)

        archive_latest_data["items"] = filtered_items

    (dst / "latest.json").write_text(
        json.dumps(archive_latest_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"📄 source: {src}")
    print(f"💾 archive: {dst}")
    print(f"🎯 archived venues: {copied_venues}")

    index_script = Path(__file__).with_name("build_archive_index.py")
    if index_script.exists():
        index_cmd = [sys.executable, str(index_script)]
        if args.tmp:
            index_cmd.append("--tmp")
        subprocess.run(index_cmd, check=True)
    else:
        print(f"⏭️ archive index script not found: {index_script}")

    fix_archive_venue_index_links(dst)
    fix_archive_race_page_links(dst)
    print("🎉 archive done")
    print("=" * 72)


if __name__ == "__main__":
    main()
