#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_archive_index.py

目的:
docs/public/archive/car7/YYYY-MM-DD/ を一覧化し、
docs/public/archive/car7/index.html を生成する。

入力:
docs/grade05/archive/*/

出力:
docs/public/archive/car7/index.html
"""

from __future__ import annotations

from pathlib import Path
import sys
import argparse


PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.public01.car7.common.config import TOP_PAGE_URL


ARCHIVE_ROOT = Path("docs/public/archive/car7")
OUTPUT_PATH = ARCHIVE_ROOT / "index.html"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tmp",
        action="store_true",
        help="tmp/public01/car7/archive を使用する",
    )
    return parser.parse_args()


def collect_archive_dates(archive_root: Path = ARCHIVE_ROOT) -> list[dict]:
    if not archive_root.exists():
        return []

    rows = []
    for path in archive_root.iterdir():
        if not path.is_dir():
            continue
        if len(path.name) != 10:
            continue

        venue_index_paths = sorted(path.glob("v*/index.html"))
        if not venue_index_paths:
            continue

        import re

        title = ""

        # 日付トップindexは廃止済みのため、会場別indexを元にタイトルを拾う
        html_text = ""

        summary_titles = []
        for pattern in [
            r"<h2[^>]*>.*?<span[^>]*>(.*?)</span>.*?</h2>",
            r"<h2[^>]*>\s*📅\s*本日の7車レース\s*<span[^>]*>(.*?)</span>\s*</h2>",
        ]:
            m = re.search(pattern, html_text, re.IGNORECASE | re.DOTALL)
            if m:
                value = re.sub(r"<[^>]+>", "", m.group(1))
                value = re.sub(r"\s+", " ", value).strip()
                if value:
                    summary_titles.append(value)
                    break

        # 日付トップの<title>は汎用名になりやすいので、まずsummary内の開催名、次に会場別indexから拾う
        venue_titles = summary_titles[:]
        for venue_index in venue_index_paths:
            try:
                venue_html = venue_index.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                venue_html = ""

            candidates = []
            for pattern in [
                r"<h1[^>]*>(.*?)</h1>",
                r"<h2[^>]*>.*?<span[^>]*>(.*?)</span>.*?</h2>",
                r"<title>(.*?)</title>",
            ]:
                m = re.search(pattern, venue_html, re.IGNORECASE | re.DOTALL)
                if m:
                    value = re.sub(r"<[^>]+>", "", m.group(1))
                    value = re.sub(r"\s+", " ", value).strip()
                    value = value.replace("競輪AIアタルくん", "").strip()
                    value = re.sub(r"^本日の7車レース\s*", "", value).strip()
                    if value:
                        candidates.append(value)

            # venue別indexの中から、開催名・開催日が入ったタイトルを優先する
            candidates = sorted(
                candidates,
                key=lambda x: (
                    "（" not in x and "日目" not in x and "初日" not in x and "最終日" not in x,
                    "カップ" not in x and "杯" not in x and "競輪" not in x,
                    -len(x),
                ),
            )

            for candidate in candidates:
                if "競輪AIアタルくん" in candidate:
                    continue
                if "7車レース予想" in candidate:
                    continue
                if candidate in {"アーカイブ", "本日の7車レース"}:
                    continue
                venue_titles.append(candidate)
                break

        if venue_titles:
            # 同じ開催名が複数経路で拾われた場合は重複排除する
            unique_titles = []
            for venue_title in venue_titles:
                if venue_title not in unique_titles:
                    unique_titles.append(venue_title)
            title = " / ".join(unique_titles)
        else:
            m = re.search(r"<title>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
                if "競輪AIアタルくん" in title:
                    title = ""

        venue_ids = sorted([p.parent.name for p in path.glob("v*/index.html")])

        if venue_ids:
            for venue_id in venue_ids:
                venue_title = title

                venue_index = path / venue_id / "index.html"
                if venue_index.exists():
                    try:
                        venue_html = venue_index.read_text(encoding="utf-8", errors="ignore")

                        candidates = []
                        for pattern in [
                            r"<h2[^>]*>.*?<span[^>]*>(.*?)</span>.*?</h2>",
                            r"<h2[^>]*>\s*📅\s*本日の7車レース\s*<span[^>]*>(.*?)</span>\s*</h2>",
                            r"<title>(.*?)</title>",
                        ]:
                            m = re.search(pattern, venue_html, re.IGNORECASE | re.DOTALL)
                            if not m:
                                continue
                            value = re.sub(r"<[^>]+>", "", m.group(1))
                            value = re.sub(r"\s+", " ", value).strip()
                            value = value.replace("競輪AIアタルくん", "").strip()
                            value = re.sub(r"^本日の7車レース\s*", "", value).strip()
                            if not value:
                                continue
                            if value in {"アーカイブ", "本日の7車レース", "7車レース予想"}:
                                continue
                            if "🏆 7車レース予想" in value:
                                continue
                            candidates.append(value)

                        if candidates:
                            candidates = sorted(
                                candidates,
                                key=lambda x: (
                                    "（" not in x and "日目" not in x and "初日" not in x and "最終日" not in x,
                                    "カップ" not in x and "杯" not in x and "競輪" not in x,
                                    -len(x),
                                ),
                            )
                            venue_title = candidates[0]
                    except Exception:
                        pass

                rows.append({
                    "date": path.name,
                    "title": venue_title,
                    "venue_id": venue_id,
                })
        else:
            rows.append({
                "date": path.name,
                "title": title,
                "venue_id": "",
            })

    return sorted(rows, key=lambda x: x["date"], reverse=True)


def top_page_href_from_archive_index() -> str:
    """docs/public/archive/car7/index.html からトップへ戻るリンクを返す。"""
    if TOP_PAGE_URL.startswith(("http://", "https://", "/")):
        return TOP_PAGE_URL
    return f"../../../{TOP_PAGE_URL}"


def archive_page_css() -> str:
    return '''
    body {
      margin: 0;
      background: #f3f4f6;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif;
    }
    .page {
      max-width: 920px;
      margin: 0 auto;
      padding: 20px 14px 40px;
    }
    .header {
      background: linear-gradient(135deg, #1d4ed8, #0f172a);
      color: white;
      border-radius: 18px;
      padding: 20px 18px;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
    }
    .header h1 {
      margin: 0 0 8px;
      font-size: 1.45rem;
    }
    .header p {
      margin: 0;
      opacity: 0.9;
      font-size: 0.95rem;
    }
    .nav {
      margin: 14px 0;
    }
    .nav a {
      display: inline-block;
      text-decoration: none;
      color: #1d4ed8;
      font-weight: 800;
      background: white;
      border: 1px solid #dbeafe;
      padding: 8px 12px;
      border-radius: 999px;
    }
    .list {
      margin-top: 16px;
      display: grid;
      gap: 12px;
    }
    .archive-item {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      text-decoration: none;
      color: inherit;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 14px;
      padding: 18px 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .archive-date {
      font-weight: 800;
      font-size: 1.05rem;
    }
    .archive-sub {
      font-size: 0.88rem;
      color: #6b7280;
      margin-top: 4px;
    }
    .archive-link {
      color: #1d4ed8;
      font-weight: 800;
      white-space: nowrap;
    }
    .empty {
      background: white;
      border-radius: 14px;
      padding: 18px;
      color: #6b7280;
    }
    '''


def build_html(rows: list[dict]) -> str:
    # トップは日付単位で表示
    top_href = top_page_href_from_archive_index()

    grouped = {}
    for row in rows:
        date = str(row.get("date", "")).strip()
        if date:
            grouped.setdefault(date, []).append(row)

    items = []
    for date in sorted(grouped.keys(), reverse=True):
        venue_count = len(grouped[date])
        items.append(
            f'''
        <a class="archive-item" href="./{date}/index.html">
          <div>
            <div class="archive-date">{date}</div>
            <div class="archive-sub">{venue_count}開催</div>
          </div>
          <div class="archive-link">開催一覧を見る →</div>
        </a>'''
        )

    items_html = "\n".join(items) if items else (
        '<div class="empty">アーカイブはまだありません。</div>'
    )

    return f'''<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>7車 予想アーカイブ</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
{archive_page_css()}
  </style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>7車 予想アーカイブ</h1>
      <p>日付を選択してください</p>
    </section>

    <div class="nav">
      <a href="{top_href}">← トップページへ戻る</a>
    </div>

    <section class="list">
      {items_html}
    </section>
  </main>
</body>
</html>
'''


def build_day_html(date: str, rows: list[dict]) -> str:
    # 日付ページはWATCH/OTHERを分けず全開催を表示
    day_rows = [
        row for row in rows
        if str(row.get("date", "")).strip() == date
    ]

    def venue_sort_key(row):
        raw = str(row.get("venue_id", "")).lstrip("vV")
        try:
            return int(raw)
        except ValueError:
            return 999

    day_rows.sort(key=venue_sort_key)

    items = []
    for row in day_rows:
        venue_id = str(row.get("venue_id", "")).strip()
        title = str(row.get("title", "")).strip()

        if not venue_id:
            continue

        display_title = title or venue_id

        items.append(
            f'''
        <a class="archive-item" href="./{venue_id}/index.html">
          <div>
            <div class="archive-date">{display_title}</div>
          </div>
          <div class="archive-link">レース一覧を見る →</div>
        </a>'''
        )

    items_html = "\n".join(items) if items else (
        '<div class="empty">開催はありません。</div>'
    )

    return f'''<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>{date} 7車予想アーカイブ</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
{archive_page_css()}
  </style>
</head>
<body>
  <main class="page">
    <section class="header">
      <h1>{date}</h1>
      <p>7車AI予想・開催一覧</p>
    </section>

    <div class="nav">
      <a href="../index.html">← 日付一覧へ戻る</a>
    </div>

    <section class="list">
      {items_html}
    </section>
  </main>
</body>
</html>
'''

def main():
    args = parse_args()

    if args.tmp:
        archive_root = Path("tmp/public01/car7/archive")
        output_path = archive_root / "index.html"
        mode = "TMP"
    else:
        archive_root = ARCHIVE_ROOT
        output_path = OUTPUT_PATH
        mode = "PUBLIC"

    dates = collect_archive_dates(archive_root)
    html = build_html(dates)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    archive_dates = sorted({
        str(row.get("date", "")).strip()
        for row in dates
        if str(row.get("date", "")).strip()
    })

    for archive_date in archive_dates:
        day_dir = archive_root / archive_date
        day_dir.mkdir(parents=True, exist_ok=True)

        day_html = build_day_html(archive_date, dates)
        (day_dir / "index.html").write_text(
            day_html,
            encoding="utf-8",
        )

    print("=" * 72)
    print("🚀 START public01 car7 build archive index")
    print("=" * 72)
    print(f"📦 archive mode: {mode}")
    print(f"📊 archive entries: {len(dates)}")
    print(f"💾 saved: {output_path}")
    print("🎉 archive index done")
    print("=" * 72)


if __name__ == "__main__":
    main()
