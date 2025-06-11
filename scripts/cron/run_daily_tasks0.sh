#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


. /Users/satomi/Documents/keirin/venv_shared/bin/activate
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web

YESTERDAY=$(date -v-1d "+%Y-%m-%d")
TODAY=$(date "+%Y-%m-%d")

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
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/entries/scrape_entry_today.py "$TODAY" \
  && echo "[OK] entry scrape completed" || echo "[FAIL] entry scrape failed"

# 5. 出走表のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_today_entry_to_duckdb.py \
  && echo "[OK] append today entry to DuckDB completed" || echo "[FAIL] append today entry to DuckDB failed"

###############################################################################
/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web
mkdir -p data/train
###############################################################################

#
# 6-9. モデル実行（run_backtest_predict0.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/3rd/run_backtest_predict0.py --start "$TODAY" --end "$TODAY" \
  && echo "[OK] run_backtest_predict0.py completed" || echo "[FAIL] run_backtest_predict0.py failed"
###############################################################################

# 10. 予測結果ファイルをGitHubへコミット
FINAL_PREDICTION_FILE="output/predict/final_prediction_${TODAY}.csv"
if [ -f "$FINAL_PREDICTION_FILE" ]; then
  git config --global user.name "GitHub Actions"
  git config --global user.email "actions@github.com"

  # 変更があるか確認してからコミット処理を行う
  git status --porcelain | grep -q . && {
    git add "$FINAL_PREDICTION_FILE"
    git commit -m "🤖 Final prediction result for ${TODAY}"
    
    # GitHubへのpush（認証情報が必要な環境では失敗する可能性あり）
    if git push origin main; then
      echo "✅ final prediction result committed to GitHub"
    else
      echo "❌ final prediction result push failed"
      echo "[FAIL] final prediction result push failed"
    fi
  } || echo "[SKIP] No changes to commit"
else
  echo "[SKIP] final prediction file not found: $FINAL_PREDICTION_FILE"
fi

# 11. Slack通知
if tail -n 50 "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" | grep -q "\[FAIL\]"; then
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "❌ 競輪タスク失敗あり: ${LOG_DATE}"
else
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "✅ 競輪タスク成功: ${LOG_DATE}"
fi

echo "=== run_daily_tasks.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="