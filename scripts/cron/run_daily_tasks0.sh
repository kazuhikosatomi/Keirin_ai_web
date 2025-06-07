#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


. /Users/satomi/Documents/keirin/venv_shared/bin/activate
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web

YESTERDAY=$(date -v-1d "+%Y-%m-%d")
TODAY=$(date "+%Y-%m-%d")

LOG_DATE=$(date +%F)
echo "=== run_daily_tasks.sh started at $(date '+%Y-%m-%d %H:%M:%S') ==="
exec >> "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" 2>&1



###############################################################################
/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web
mkdir -p data/train
###############################################################################

###############################################################################

# 10. 予測結果ファイルをGitHubへコミット
PREDICTED_RANK_FILE="output/predict/train.predicted_rank_${TODAY}.csv"
if [ -f "$PREDICTED_RANK_FILE" ]; then
  git config --global user.name "GitHub Actions"
  git config --global user.email "actions@github.com"
  git pull origin main --rebase
  git add "$PREDICTED_RANK_FILE"
  git commit -m "🤖 Predict result for ${TODAY}"
  git push origin main \
    && echo "✅ predict result committed to GitHub" \
    || echo "❌ predict result commit failed"
else
  echo "[SKIP] predict result file not found: $PREDICTED_RANK_FILE"
fi

# 11. Slack通知
if tail -n 50 "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" | grep -q "\[FAIL\]"; then
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "❌ 競輪タスク失敗あり: ${LOG_DATE}"
else
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "✅ 競輪タスク成功: ${LOG_DATE}"
fi

echo "=== run_daily_tasks.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="