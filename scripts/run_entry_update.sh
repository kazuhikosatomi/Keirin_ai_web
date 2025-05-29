#!/bin/bash

# 日時ログ出力
echo "===== $(date '+%Y-%m-%d %H:%M:%S') Start ====="

# 仮想環境のアクティベート
source ~/venv_shared/bin/activate

# 作業ディレクトリへ移動
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts

# 今日の日付を取得（YYYYMMDD形式）
TODAY=$(date '+%Y%m%d')

# 出走表のスクレイピング（最新）
echo "▶️ Running scrape_entry.py for $TODAY..."
python3 entries/scrape_entry.py $TODAY

# DuckDBへのappend
echo "▶️ Running append_today_entry_to_duckdb.py..."
python3 append/append_today_entry_to_duckdb.py

echo "===== $(date '+%Y-%m-%d %H:%M:%S') Finished ====="