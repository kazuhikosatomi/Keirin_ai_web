#!/bin/bash

# 1. オッズのスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/odds/scrape_odds_headless_yesterday.py

# 2. 結果のスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/results/scrape_results_headless_yesterday.py

# 3. odds + results のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_yesterday_to_duckdb.py

# 4. 出走表のスクレイピング（当日を引数に指定）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/entry/scrape_entry.py $(date +\%F)

# 5. 出走表のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_today_entry_to_duckdb.py
