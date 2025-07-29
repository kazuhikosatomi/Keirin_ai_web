#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


. /Users/satomi/Documents/keirin/venv_shared/bin/activate
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web

if [ -n "$1" ]; then
  TODAY="$1"
else
  TODAY=$(date "+%Y-%m-%d")
fi
YESTERDAY=$(date -j -v-1d -f "%Y-%m-%d" "$TODAY" "+%Y-%m-%d")

echo "▶ TODAY = $TODAY"
echo "▶ YESTERDAY = $YESTERDAY"

LOG_DATE=$(date +%F)
echo "=== run_daily_tasks.sh00 started at $(date '+%Y-%m-%d %H:%M:%S') ==="
exec >> "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" 2>&1

# 1. オッズのスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/odds/scrape_odds_headless_yesterday.py --target "$YESTERDAY" \
  && echo "[OK] odds scrape completed" || echo "[FAIL] odds scrape failed"


# 2. 結果のスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/results/scrape_results_headless_yesterday.py --target "$YESTERDAY" \
  && echo "[OK] results scrape completed" || echo "[FAIL] results scrape failed"


# 2.5. グレード情報のスクレイピング
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/grade/scrape_race_grade_fast.py --target "$YESTERDAY" \
  && echo "[OK] race grade scrape completed" || echo "[FAIL] race grade scrape failed"

# 2.6. results に race_grade をマージ
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/merge_results_with_grade.py --target "$YESTERDAY" \
  && echo "[OK] merge results with grade completed" || echo "[FAIL] merge results with grade failed"

# 3. odds + results のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_yesterday_to_duckdb.py --target "$YESTERDAY" \
  && echo "[OK] append to DuckDB completed" || echo "[FAIL] append to DuckDB failed"

# 4. 出走表のスクレイピング（当日を引数に指定）
# 当日分の出走表
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/entries/scrape_entry_today_grade.py "$TODAY" \
  && echo "[OK] entry scrape completed (today)" || echo "[FAIL] entry scrape failed (today)"

# 前日分の出走表も取得し直す
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/entries/scrape_entry_today_grade.py "$YESTERDAY" \
  && echo "[OK] entry scrape completed (yesterday)" || echo "[FAIL] entry scrape failed (yesterday)"

# 5. 出走表のDB登録
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_today_entry_to_duckdb.py --target "$TODAY" \
  && echo "[OK] append today entry to DuckDB completed" || echo "[FAIL] append today entry to DuckDB failed"
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/append/append_today_entry_to_duckdb.py --target "$YESTERDAY" \
  && echo "[OK] append yesterday entry to DuckDB completed" || echo "[FAIL] append yesterday entry to DuckDB failed"

# 5.5 荒れ度分析ステップ（scripts/arare/）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 scripts/arare/arare0_arare_label.py --date "$TODAY" \
  && echo "[OK] arare0_arare_label.py completed" || echo "[FAIL] arare0_arare_label.py failed"

 /Users/satomi/Documents/keirin/venv_shared/bin/python3 scripts/arare/arare1_race_stats.py --date "$TODAY" \
  && echo "[OK] arare1_race_stats.py completed" || echo "[FAIL] arare1_race_stats.py failed"

 /Users/satomi/Documents/keirin/venv_shared/bin/python3 scripts/arare/arare2_merge.py --date "$TODAY" \
  && echo "[OK] arare2_merge.py completed" || echo "[FAIL] arare2_merge.py failed"
###############################################################################
cd /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web
mkdir -p data/train
###############################################################################

# 6-9a. モデル実行（run_backtest_predict_niren.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/3rd/run_daily_predict_niren.py --date "$TODAY" \
  && echo "[OK] run_backtest_predict_niren.py completed" || echo "[FAIL] run_backtest_predict_niren.py failed"

# 6-9b. モデル実行（run_backtest_predict_trio.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/4th/run_daily_predict_trio.py --date "$TODAY"  \
  && echo "[OK] run_backtest_predict_trio.py completed" || echo "[FAIL] run_backtest_predict_trio.py failed"

# 6-9c. モデル実行（run_backtest_predict_arare.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/5th/run_daily_predict_arare.py --date "$TODAY" \
  && echo "[OK] run_backtest_predict_arare.py completed" || echo "[FAIL] run_backtest_predict_arare.py failed"

# 6-9d. モデル実行（run_backtest_predict_arare_race.py）
/Users/satomi/Documents/keirin/venv_shared/bin/python3 /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/8th/run_daily_predict_arare_race.py --date "$TODAY" \
  && echo "[OK] run_backtest_predict_arare_race.py completed" || echo "[FAIL] run_backtest_predict_arare_race.py failed"
###############################################################################

# 10. 予測結果ファイルをGitHubへコミット
FINAL_PREDICTION_FILE="docs/predict/csv/3nd/final_prediction_niren_${TODAY}.csv"
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

FINAL_PREDICTION_PDF="docs/predict/pdf/3nd/final_prediction_niren_${TODAY}.pdf"
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

echo "#11: Add yesterday's PDF to archive"
YESTERDAY=$(date -v-1d "+%Y-%m-%d")
YESTERDAY_FILE="docs/predict/pdf/3nd/final_prediction_niren_${YESTERDAY}.pdf"
ARCHIVE_HTML="docs/archive.html"

if [ -f "$YESTERDAY_FILE" ]; then
  # 日付形式を変換（例: 2025-06-20 → 2025年6月20日）
  #JP_DATE=$(date -jf "%Y-%m-%d" "$YESTERDAY" "+%Y年%-m月%-d日")
  JP_DATE="${YESTERDAY} の予想"
  # すでにリンクが存在しない場合のみ追記
  if ! grep -q "$YESTERDAY_FILE" "$ARCHIVE_HTML"; then
    INSERT_LINE="    <li><a href=\"predict/pdf/3nd/final_prediction_niren_${YESTERDAY}.pdf\" target=\"_blank\">${JP_DATE}</a></li>"
    awk -v insert="$INSERT_LINE" '/<!-- ARCHIVE_INSERT_POINT -->/ {
        print;
        print insert;
        next
    }1' "$ARCHIVE_HTML" > "${ARCHIVE_HTML}.tmp" && mv "${ARCHIVE_HTML}.tmp" "$ARCHIVE_HTML"
    echo "✅ アーカイブに ${YESTERDAY} のPDFリンクを追加しました（AWK方式）"

    # archive.html を GitHub にコミット・プッシュ
    if git status --porcelain | grep -q 'docs/archive.html'; then
      git add docs/archive.html
      git commit -m "📚 Update archive with ${YESTERDAY} PDF link"
      if git push origin main; then
        echo "✅ archive.html pushed to GitHub"
      else
        echo "❌ archive.html push failed"
      fi
    else
      echo "[SKIP] archive.html has no changes"
    fi
  fi
else
  echo "⚠️ 前日 (${YESTERDAY}) のPDFが存在しません"
fi

TODAY_JP=$(date -j -f "%Y-%m-%d" "$TODAY" "+%Y年%-m月%-d日")
PDF_FILE_NAME="final_prediction_niren_${TODAY}.pdf"
INDEX_HTML_PATH="./docs/index.html"

# index.htmlの中のリンク部分を書き換える（macOS用）
sed -i '' -E "s|href=\"./predict/pdf/3nd/final_prediction_niren_.*.pdf\"|href=\"./predict/pdf/3nd/${PDF_FILE_NAME}\"|g" "${INDEX_HTML_PATH}"
sed -i '' -E "s|PDFを開く（.*）|PDFを開く（${TODAY_JP}）|g" "${INDEX_HTML_PATH}"

if git status --porcelain | grep -q 'docs/index.html'; then
  git add docs/index.html
  git commit -m "🌐 Update index.html with today's prediction link (${TODAY})"
  if git push origin main; then
    echo "✅ index.html pushed to GitHub"
  else
    echo "❌ index.html push failed"
  fi
else
  echo "[SKIP] index.html has no changes"
fi

echo "=== run_daily_tasks.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="

# 12. Slack通知
if tail -n 50 "/Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" | grep -q "\[FAIL\]"; then
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "❌ 競輪タスク失敗あり: ${LOG_DATE}"
else
  /Users/satomi/Documents/keirin/GitHub/Keirin_ai_web/scripts/cron/send_slack.sh "✅ 競輪タスク成功: ${LOG_DATE}"
fi