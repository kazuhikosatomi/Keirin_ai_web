#!/bin/bash
# cron から起動するため、すべてフルパスで記述します

# 仮想環境の有効化
source /Users/satomi/Documents/keirin/venv_shared/bin/activate

# 作業ディレクトリへ移動
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web

# スクリプト実行（ログも保存）
/usr/bin/python3 scripts/append/append_yesterday_to_duckdb.py >> logs/append_daily.log 2>&1