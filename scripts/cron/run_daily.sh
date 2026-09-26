#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


. /Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/activate
cd /Users/satomi/keirin/GitHub/keirin_ai_web

#
# 日付指定:
#   run_daily.sh                 -> 今日
#   run_daily.sh 2026-04-25      -> 指定日
#   run_daily.sh --date 2026-04-25 -> 指定日
if [ "$1" = "--date" ]; then
  if [ -z "$2" ]; then
    echo "[ERROR] --date requires YYYY-MM-DD"
    exit 1
  fi
  TODAY="$2"
elif [ -n "$1" ]; then
  TODAY="$1"
else
  TODAY=$(date "+%Y-%m-%d")
fi

YESTERDAY=$(date -j -v-1d -f "%Y-%m-%d" "$TODAY" "+%Y-%m-%d")

echo "▶ TODAY = $TODAY"
echo "▶ YESTERDAY = $YESTERDAY"

LOG_DATE=$(date +%F)
RUN_LOG="/Users/satomi/keirin/GitHub/keirin_ai_web/logs/run_daily/run_daily_${LOG_DATE}.log"
echo "=== run_daily.sh started at $(date '+%Y-%m-%d %H:%M:%S') ==="
# cron側で RUN_LOG にリダイレクトしているため、ここで daily_tasks へ切り替えない
# exec >> "/Users/satomi/keirin/GitHub/keirin_ai_web/logs/daily_tasks_${LOG_DATE}.log" 2>&1

# 1. オッズのスクレイピング
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/01scrape_odds.py --date "$YESTERDAY" \
  && echo "[OK] odds scrape completed" || echo "[FAIL] odds scrape failed"


# 2. 結果のスクレイピング
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/02scrape_results.py --date "$YESTERDAY" \
  && echo "[OK] results scrape completed" || echo "[FAIL] results scrape failed"


# 3. グレード情報のスクレイピング
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/03scrape_race_grade.py --date "$YESTERDAY" \
  && echo "[OK] race grade scrape completed" || echo "[FAIL] race grade scrape failed"

# 4. results に race_grade をマージ
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/04merge_results_with_grade.py --date "$YESTERDAY" \
  && echo "[OK] merge results with grade completed" || echo "[FAIL] merge results with grade failed"


# 5. 出走表のスクレイピング（当日を引数に指定）
# 当日分の出走表
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/05scrape_entry.py --date "$TODAY" \
  && echo "[OK] entry scrape completed (today)" || echo "[FAIL] entry scrape failed (today)"


# 前日分の出走表も取得し直す
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/05scrape_entry.py --date "$YESTERDAY" \
  && echo "[OK] entry scrape completed (yesterday)" || echo "[FAIL] entry scrape failed (yesterday)"


# 6. WINTICKET 出走表 S/H/B・発走時間のスクレイピング
# 当日分
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/06scrape_winticket_entry_shb.py --date "$TODAY" \
  && echo "[OK] winticket S/H/B scrape completed (today)" || echo "[FAIL] winticket S/H/B scrape failed (today)"

# 前日分
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/06scrape_winticket_entry_shb.py --date "$YESTERDAY" \
  && echo "[OK] winticket S/H/B scrape completed (yesterday)" || echo "[FAIL] winticket S/H/B scrape failed (yesterday)"

# 7. WINTICKET S/H/B・発走時間を entry にマージ
# 当日分
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/07merge_winticket_shb_to_entry.py --date "$TODAY" \
  && echo "[OK] merge winticket S/H/B to entry completed (today)" || echo "[FAIL] merge winticket S/H/B to entry failed (today)"

# 前日分
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/07merge_winticket_shb_to_entry.py --date "$YESTERDAY" \
  && echo "[OK] merge winticket S/H/B to entry completed (yesterday)" || echo "[FAIL] merge winticket S/H/B to entry failed (yesterday)"


# 7a. OddsPark 出走表のスクレイピング（当日・前日）
# まずは WinTicket 系と並走。安定後に entry 主系を OddsPark へ切替予定。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/08scrape_oddspark_entry.py --date "$TODAY" \
  && echo "[OK] oddspark entry scrape completed (today)" || echo "[FAIL] oddspark entry scrape failed (today)"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/fix/08scrape_oddspark_entry.py --date "$YESTERDAY" \
  && echo "[OK] oddspark entry scrape completed (yesterday)" || echo "[FAIL] oddspark entry scrape failed (yesterday)"


# 7b. feature_base master train 作成（前日分）
# results が確定した前日分を正式feature_base master trainとして作成。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/feature_base/master/run_feature_base_train_master.py --date "$YESTERDAY" \
  && echo "[OK] feature_base master train completed (yesterday)" || echo "[FAIL] feature_base master train failed (yesterday)"

# 7c. feature_base master predict 作成（当日分）
# 当日予測用。resultsを使わない正式feature_base master predictを作成。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/feature_base/master/run_feature_base_predict_master.py --date "$TODAY" \
  && echo "[OK] feature_base master predict completed (today)" || echo "[FAIL] feature_base master predict failed (today)"


# 7d. core_b car9 作成（前日分・当日分）
# 念のため前日分を再作成後、当日分を作成する。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_b/car9/run_core_b_car9_morning.py --date "$YESTERDAY" \
  && echo "[OK] core_b car9 completed (yesterday)" || echo "[FAIL] core_b car9 failed (yesterday)"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_b/car9/run_core_b_car9_morning.py --date "$TODAY" \
  && echo "[OK] core_b car9 completed (today)" || echo "[FAIL] core_b car9 failed (today)"

# 7d-2. core_b car7 作成（前日分・当日分）
# car9と同様、朝専用runnerでStep01〜03のみ実行する。
# 当日results未取得でもStep04評価を行わないため正常終了できる。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_b/car7/run_core_b_car7_morning.py --date "$YESTERDAY" \
  && echo "[OK] core_b car7 completed (yesterday)" || echo "[FAIL] core_b car7 failed (yesterday)"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_b/car7/run_core_b_car7_morning.py --date "$TODAY" \
  && echo "[OK] core_b car7 completed (today)" || echo "[FAIL] core_b car7 failed (today)"

# 7e. core_win car9 作成（前日分・当日分）
# 念のため前日分を再作成後、当日分を作成する。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_win/car9/run_core_win_car9_morning.py --date "$YESTERDAY" --train-days 365 \
  && echo "[OK] core_win car9 completed (yesterday)" || echo "[FAIL] core_win car9 failed (yesterday)"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/core_win/car9/run_core_win_car9_morning.py --date "$TODAY" --train-days 365 \
  && echo "[OK] core_win car9 completed (today)" || echo "[FAIL] core_win car9 failed (today)"


# 7f. chance01 car9 作成（当日分）
# 前日D-1のfeedback対象を判定して履歴を更新。
# 当日Dはcommonの正式9車判定
# （9車・L1除外・外国人含有レース除外）を確認し、
# 対象ありの場合のみ Step01〜08 を実行する。
# payout側でchance出力を利用できるよう、payoutより前に実行する。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 \
  /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/chance01/car9/run_chance01_car9.py \
  --date "$TODAY" \
  && echo "[OK] chance01 car9 completed (today)" \
  || echo "[FAIL] chance01 car9 failed (today)"


# 7g. payout01 car9 Base30 作成（当日分）
# commonの正式9車判定
# （9車・L1除外・外国人含有レース除外）を事前確認。
# 対象ありの場合のみ Step01〜06 → Step08 → Step09 を実行する。
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 \
  /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/payout01/car9/run_payout01_car9.py \
  --date "$TODAY" \
  && echo "[OK] payout01 car9 completed (today)" \
  || echo "[FAIL] payout01 car9 failed (today)"


###############################################################################
cd /Users/satomi/keirin/GitHub/keirin_ai_web
mkdir -p data/train
###############################################################################

# 8-9a. モデル実行gr01（run_daily_predict.py）
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/gr01/run_daily_predict.py --date "$TODAY" \
  && echo "[OK] run_daily_predict.py completed" || echo "[FAIL] run_daily_predict.py failed"

# grade05/index_grade05.html 用: 本日の全レース予想PDF latest.json を生成
PDF_FILE_NAME="final_prediction_v2_${TODAY}.pdf"
PDF_LATEST_JSON="docs/predict/pdf/gr01/latest.json"
mkdir -p "$(dirname "$PDF_LATEST_JSON")"
python3 - <<PY
from pathlib import Path
import json

today = "${TODAY}"
out = Path("${PDF_LATEST_JSON}")
out.write_text(
    json.dumps(
        {
            "href": f"./predict/pdf/gr01/final_prediction_v2_{today}.pdf",
            "label": f"全レース予想（{today}）",
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(f"[OK] wrote {out}")
PY

# gr01公開ファイルを直近30日分に同期し、archive.htmlを実在PDFから再生成
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/gr01/sync_public_gr01_outputs.py --keep-days 30 \
  && echo "[OK] sync_public_gr01_outputs.py completed" || echo "[FAIL] sync_public_gr01_outputs.py failed"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/gr01/build_gr01_archive_index.py \
  && echo "[OK] build_gr01_archive_index.py completed" || echo "[FAIL] build_gr01_archive_index.py failed"

###############################################################################

# 10. 予測結果ファイルをGitHubへコミット

# 対象ファイルを配列にまとめる
FILES_TO_COMMIT=(
  "docs/predict/pdf/gr01"
  "docs/results/pdf/gr01"
  "docs/predict/pdf/gr01/latest.json"
  "docs/archive.html"
)

# 各ファイルをチェックして add
CHANGED=false
for FILE in "${FILES_TO_COMMIT[@]}"; do
  if [ -e "$FILE" ]; then
    git add -A "$FILE"
    CHANGED=true
    echo "📝 added: $FILE"
  else
    echo "⚠️ file not found: $FILE"
  fi
done

# 変更があればコミットと push
if $CHANGED && git status --porcelain | grep -q .; then
  git commit -m "🤖 Final predictions and results for ${TODAY}"
  
  if git push origin main; then
    echo "✅ All prediction files committed and pushed to GitHub"
  else
    echo "❌ GitHub push failed"
  fi
else
  echo "[SKIP] No changes to commit"
fi

# ========================================
# トップページ docs/index.html
# ========================================
# 2026-09-21:
# 新トップは docs/predict/pdf/gr01/latest.json を参照して
# 本日の全レースPDFを表示する方式へ移行。
#
# そのため、旧仕様の
#   - docs/index.html の日付入りPDFリンク直接書換
#   - docs/index.html の自動 git add / commit / push
# は廃止する。
#
# トップページはデザイン・公開構成確定後に手動で公開する。
echo "[SKIP] docs/index.html auto update/publish disabled (latest.json mode)"



# 11.5 展開AI / 荒れAI / top3AI の日次実行
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/tenkai01/run_daily_tenkai01.py --date "$TODAY" \
  && echo "[OK] run_daily_tenkai01.py completed" || echo "[FAIL] run_daily_tenkai01.py failed"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/arare02/run_daily_arare02.py --date "$TODAY" \
  && echo "[OK] run_daily_arare02.py completed" || echo "[FAIL] run_daily_arare02.py failed"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/top3racer01/run_daily_top3racer01.py --date "$TODAY" \
  && echo "[OK] run_daily_top3racer01.py completed" || echo "[FAIL] run_daily_top3racer01.py failed"

# ========================================
# sim06 日次実行
# ========================================
/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 \
  /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/sim06/run_daily_sim06.py \
  --date "$TODAY" \
  && echo "[OK] run_daily_sim06.py completed" \
  || echo "[FAIL] run_daily_sim06.py failed"

# ========================================
# grade05 実行（表示生成）
# ========================================
echo "========================================"
echo "🎯 START grade05 morning"
echo "========================================"

bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/grade05/run/run_grade05_morning.sh "$TODAY"

# ========================================
# bet01 car9 毎朝運用
# B1 + feedback 正式運用
# ========================================
if true; then
echo "========================================"
echo "🎯 START bet01 car9 daily"
echo "========================================"

bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/bet01/car9/run_morning_bet01_car9.sh "$TODAY" \
  && echo "[OK] run_morning_bet01_car9.sh completed" \
  || echo "[FAIL] run_morning_bet01_car9.sh failed"
fi

# ========================================
# bet01 car7 毎朝運用
# 前日D-1の評価・feedback → 当日Dの予測
# feedback=1 / sim06_weight=0 はmorning runner側の正式設定
# ========================================
echo "========================================"
echo "🎯 START bet01 car7 daily"
echo "========================================"

bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/bet01/car7/run_morning_bet01_car7.sh "$TODAY" \
  && echo "[OK] run_morning_bet01_car7.sh completed" \
  || echo "[FAIL] run_morning_bet01_car7.sh failed"

# ========================================
# chance01 car7 毎朝運用
# D-1まででStep01〜06を学習し、DでStep07〜08を予測する。
# payout01/car7でchance出力を利用するためpayoutより前に実行する。
# ========================================
echo "========================================"
echo "🎯 START chance01 car7 daily"
echo "========================================"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 \
  /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/chance01/car7/run_chance01_car7.py \
  --date "$TODAY" \
  && echo "[OK] chance01 car7 completed (today)" \
  || echo "[FAIL] chance01 car7 failed (today)"

# ========================================
# payout01 car7 毎朝運用
# D-1までで学習し、DのStep08〜09予測を作成する。
# bet01/car7・chance01/car7・core_b/car7の生成後に実行する。
# ========================================
echo "========================================"
echo "🎯 START payout01 car7 daily"
echo "========================================"

/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python3 \
  /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/payout01/car7/run_payout01_car7.py \
  --date "$TODAY" \
  && echo "[OK] payout01 car7 completed (today)" \
  || echo "[FAIL] payout01 car7 failed (today)"

# ========================================
# public01 car7 毎朝運用
# payout01/car7完了後に当日全対象のページを生成・latest同期する。
# morning成功後はwatchをバックグラウンド起動する。
# watch_targets未作成時はwatch側で待機し、手動選択後に開始する。
# ========================================
echo "========================================"
echo "🧪 START public01 car7 morning (LOCAL)"
echo "========================================"

PUBLIC01_PUBLISH=1 bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/public01/car7/run/run_public01_car7_morning.sh "$TODAY"
PUBLIC01_CAR7_MORNING_RC=$?

if [ "$PUBLIC01_CAR7_MORNING_RC" -eq 0 ]; then
  echo "[OK] run_public01_car7_morning.sh completed"

  # 当日に正式な7車対象レースがある場合だけwatchを起動する。
  python3 scripts/common/check_car7_day.py --date "$TODAY" --json
  PUBLIC01_CAR7_RC=$?

  if [ "$PUBLIC01_CAR7_RC" -eq 0 ]; then
    echo "👀 public01 car7 watch をバックグラウンド起動 | $TODAY"

    mkdir -p data/public01/car7/watch

    nohup env PUBLIC01_PUBLISH=1       bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/public01/car7/run/run_public01_car7_watch.sh "$TODAY"       > "data/public01/car7/watch/public01_car7_watch_${TODAY}.log" 2>&1 &

    PUBLIC01_CAR7_WATCH_PID=$!

    echo "✅ public01 car7 watch 起動要求完了 | pid=$PUBLIC01_CAR7_WATCH_PID"
    echo "📝 log: data/public01/car7/watch/public01_car7_watch_${TODAY}.log"

    echo "🏁 public01 car7 OTHER finalize runner をバックグラウンド起動 | $TODAY"

    nohup env PUBLIC01_PUBLISH=1 \
      bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/public01/car7/run/run_public01_car7_other_finalize.sh "$TODAY" \
      > "data/public01/car7/watch/public01_car7_other_finalize_${TODAY}.log" 2>&1 &

    PUBLIC01_CAR7_OTHER_PID=$!

    echo "✅ public01 car7 OTHER finalize runner 起動要求完了 | pid=$PUBLIC01_CAR7_OTHER_PID"
    echo "📝 log: data/public01/car7/watch/public01_car7_other_finalize_${TODAY}.log"

  elif [ "$PUBLIC01_CAR7_RC" -eq 1 ]; then
    echo "⏭️ 当日7車なし → public01 car7 watchは起動しません | $TODAY"

  else
    echo "⚠️ 当日7車判定失敗 → public01 car7 watchは起動しません | rc=$PUBLIC01_CAR7_RC"
  fi

else
  echo "[FAIL] run_public01_car7_morning.sh failed | rc=$PUBLIC01_CAR7_MORNING_RC"
  echo "⏭️ public01 car7 morning失敗のためwatchは起動しません"
fi

# ========================================
# public01 car9 毎朝運用
# bet01 完了後に当日の公開ページを生成し、GitHubへ反映する。
# morning成功後はwatchをバックグラウンド起動する。
# ========================================
echo "========================================"
echo "🌐 START public01 car9 morning"
echo "========================================"

PUBLIC01_PUBLISH=1 bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/public01/car9/run/run_public01_car9_morning.sh "$TODAY"
PUBLIC01_MORNING_RC=$?

if [ "$PUBLIC01_MORNING_RC" -eq 0 ]; then
  echo "[OK] run_public01_car9_morning.sh completed"

  # 当日に正式な9車対象レースがある場合だけwatchを起動する。
  python3 scripts/common/check_car9_day.py --date "$TODAY" --json
  PUBLIC01_CAR9_RC=$?

  if [ "$PUBLIC01_CAR9_RC" -eq 0 ]; then
    echo "👀 public01 car9 watch をバックグラウンド起動 | $TODAY"

    mkdir -p data/public01/car9/watch

    nohup env PUBLIC01_PUBLISH=1 \
      bash /Users/satomi/keirin/GitHub/keirin_ai_web/scripts/public01/car9/run/run_public01_car9_watch.sh "$TODAY" \
      > "data/public01/car9/watch/public01_car9_watch_${TODAY}.log" 2>&1 &

    PUBLIC01_WATCH_PID=$!

    echo "✅ public01 car9 watch 起動要求完了 | pid=$PUBLIC01_WATCH_PID"
    echo "📝 log: data/public01/car9/watch/public01_car9_watch_${TODAY}.log"

  elif [ "$PUBLIC01_CAR9_RC" -eq 1 ]; then
    echo "⏭️ 当日9車なし → public01 watchは起動しません | $TODAY"

  else
    echo "⚠️ 当日9車判定失敗 → public01 watchは起動しません | rc=$PUBLIC01_CAR9_RC"
  fi

else
  echo "[FAIL] run_public01_car9_morning.sh failed | rc=$PUBLIC01_MORNING_RC"
  echo "⏭️ public01 morning失敗のためwatchは起動しません"
fi

echo "=== run_daily.sh ended at $(date '+%Y-%m-%d %H:%M:%S') ==="
