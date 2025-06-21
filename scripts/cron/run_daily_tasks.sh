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

# 6-9. モデル実行（run_backtest_predict_niren.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/6th/run_daily_predict_niren.py \
  && echo "[OK] run_backtest_predict_niren.py completed" || echo "[FAIL] run_backtest_predict_niren.py failed"

# 6-9b. モデル実行（run_backtest_predict_trio.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/4th/run_daily_predict_trio.py  \
  && echo "[OK] run_backtest_predict_trio.py completed" || echo "[FAIL] run_backtest_predict_trio.py failed"

# 6-9c. モデル実行（run_backtest_predict_arare.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/5th/run_daily_predict_arare.py \
  && echo "[OK] run_backtest_predict_arare.py completed" || echo "[FAIL] run_backtest_predict_arare.py failed"
###############################################################################

# 10. 予測結果ファイルをGitHubへコミット
FINAL_PREDICTION_FILE="output/predict/csv/6th/final_prediction_niren_${TODAY}.csv"
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

FINAL_PREDICTION_PDF="docs/predict/pdf/6th/final_prediction_niren_${TODAY}.pdf"
if [ -f "$FINAL_PREDICTION_PDF" ]; then
  git status --porcelain | grep -q . && {
    git add "$FINAL_PREDICTION_PDF"
    git commit -m "📄 Final prediction PDF for ${TODAY}"

    if git push origin main; then
      echo "✅ final prediction PDF committed to GitHub"
    else
      echo "❌ final prediction PDF push failed"
      echo "[FAIL] final prediction PDF push failed"
    fi
  } || echo "[SKIP] No PDF changes to commit"
else
  echo "[SKIP] final prediction PDF file not found: $FINAL_PREDICTION_PDF"
fi

FINAL_PREDICTION_TRIO_FILE="output/predict/4th/final_prediction_trio_${TODAY}.csv"
if [ -f "$FINAL_PREDICTION_TRIO_FILE" ]; then
  git config --global user.name "GitHub Actions"
  git config --global user.email "actions@github.com"

  git status --porcelain | grep -q . && {
    git add "$FINAL_PREDICTION_TRIO_FILE"
    git commit -m "🤖 Final TRIO prediction result for ${TODAY}"

    if git push origin main; then
      echo "✅ final TRIO prediction result committed to GitHub"
    else
      echo "❌ final TRIO prediction result push failed"
      echo "[FAIL] final TRIO prediction result push failed"
    fi
  } || echo "[SKIP] No TRIO changes to commit"
else
  echo "[SKIP] final TRIO prediction file not found: $FINAL_PREDICTION_TRIO_FILE"
fi

FINAL_PREDICTION_ARARE_FILE="output/predict/5th/final_prediction_arare_${TODAY}.csv"
if [ -f "$FINAL_PREDICTION_ARARE_FILE" ]; then
  git config --global user.name "GitHub Actions"
  git config --global user.email "actions@github.com"

  git status --porcelain | grep -q . && {
    git add "$FINAL_PREDICTION_ARARE_FILE"
    git commit -m "🤖 Final ARARE prediction result for ${TODAY}"

    if git push origin main; then
      echo "✅ final ARARE prediction result committed to GitHub"
    else
      echo "❌ final ARARE prediction result push failed"
      echo "[FAIL] final ARARE prediction result push failed"
    fi
  } || echo "[SKIP] No ARARE changes to commit"
else
  echo "[SKIP] final ARARE prediction file not found: $FINAL_PREDICTION_ARARE_FILE"
fi

# 11. Slack通知
if tail -n 50 "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" | grep -q "\[FAIL\]"; then
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "❌ 競輪タスク失敗あり: ${LOG_DATE}"
else
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "✅ 競輪タスク成功: ${LOG_DATE}"
fi

echo "=== run_daily_tasks.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="