#!/bin/bash

source /Users/satomi/Documents/keirin/venv_shared/bin/activate

YESTERDAY=$(date -v-1d "+%Y-%m-%d")

LOG_DATE=$(date +%F)
echo "=== run_daily_tasks.sh started at $(date '+%Y-%m-%d %H:%M:%S') ==="
exec >> "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" 2>&1

# 1. オッズのスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/odds/scrape_odds_headless_yesterday.py \
  && echo "[OK] odds scrape completed" || echo "[FAIL] odds scrape failed"

# 2. 結果のスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/results/scrape_results_headless_yesterday.py \
  && echo "[OK] results scrape completed" || echo "[FAIL] results scrape failed"

# 3. odds + results のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_yesterday_to_duckdb.py \
  && echo "[OK] append to DuckDB completed" || echo "[FAIL] append to DuckDB failed"

# 4. 出走表のスクレイピング（当日を引数に指定）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/entries/scrape_entry.py $(date +\%F) \
  && echo "[OK] entry scrape completed" || echo "[FAIL] entry scrape failed"

# 5. 出走表のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_today_entry_to_duckdb.py \
  && echo "[OK] append today entry to DuckDB completed" || echo "[FAIL] append today entry to DuckDB failed"

# 6. Slack通知
#if tail -n 50 "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" | grep -q "\[FAIL\]"; then
#  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "❌ 競輪タスク失敗あり: ${LOG_DATE}"
#else
#  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "✅ 競輪タスク成功: ${LOG_DATE}"
#fi

###############################################################################
# 7. 学習データ生成（前日まで）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/train/generate_train_racer_level.py --start_date 2025-01-01 --end_date $YESTERDAY \
  && echo "[OK] train racer level data generated" || echo "[FAIL] train racer level generation failed"

# 8. モデル学習（前日まで）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/train/train_rank_model.py --train_until "$YESTERDAY" \
  && echo "[OK] rank model training completed" || echo "[FAIL] rank model training failed"

# 9. 特徴量生成（当日）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/predict/generate_predict_features.py --entry_date $(date "+%Y-%m-%d") \
  && echo "[OK] predict features generation completed" || echo "[FAIL] predict features generation failed"

# 10. 順位予測（当日）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/predict/predict_rank.py --entry_date $(date "+%Y-%m-%d") \
  && echo "[OK] predict rank completed" || echo "[FAIL] predict rank failed"
###############################################################################

echo "=== run_daily_tasks.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="
