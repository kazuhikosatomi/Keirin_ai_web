#!/bin/bash

# 仮想環境有効化
source /Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/activate

# 念のためプロジェクトルートへ移動
cd /Users/satomi/keirin/GitHub/keirin_ai_web

DATE=${1:-$(date +%Y-%m-%d)}
export PYTHON="/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python"
FINAL_AUTO_STOP_MINUTES=20
PRE_FIRST_REFRESH_INTERVAL_MINUTES=30
set -e

echo "========================================"
echo "👀 START public01 car9 watch | $DATE"
echo "========================================"

PUBLIC01_PUBLISH="${PUBLIC01_PUBLISH:-0}"

# -----------------------------------
# 二重起動防止
# 同じ日付のpublic01 watchは1本だけ動かす
# -----------------------------------
WATCH_PID_DIR="data/public01/car9/watch"
WATCH_PID_FILE="${WATCH_PID_DIR}/.public01_car9_watch_${DATE}.pid"

mkdir -p "$WATCH_PID_DIR"

if [ -f "$WATCH_PID_FILE" ]; then
  OLD_PID=$(cat "$WATCH_PID_FILE" 2>/dev/null || true)

  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "⏭️ public01 car9 watch already running | date=$DATE | pid=$OLD_PID"
    exit 0
  fi

  echo "🧹 stale watch pid file removed | $WATCH_PID_FILE"
  rm -f "$WATCH_PID_FILE"
fi

echo $$ > "$WATCH_PID_FILE"

cleanup_watch_pid() {
  if [ -f "$WATCH_PID_FILE" ]; then
    CURRENT_PID=$(cat "$WATCH_PID_FILE" 2>/dev/null || true)

    if [ "$CURRENT_PID" = "$$" ]; then
      rm -f "$WATCH_PID_FILE"
    fi
  fi
}

trap cleanup_watch_pid EXIT INT TERM

echo "🔒 public01 watch pid registered | date=$DATE | pid=$$"

publish_if_updated() {
  local result_code="$1"
  local label="$2"

  if [ "$result_code" = "2" ]; then
    echo "🧱 ${label}: snapshot → final | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/build_final_from_snapshot.py --force

    echo "🔄 ${label}: local sync → docs/public | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/publish/local_sync.py

    if [ "$PUBLIC01_PUBLISH" = "1" ]; then
      echo "🚀 ${label}: publish final/archive | $(date '+%Y-%m-%d %H:%M:%S')"
      $PYTHON scripts/public01/car9/publish/git_publish.py         || echo "⚠️ public01 git publish failed, but watch shell continues."
    else
      echo "🧪 ${label}: LOCAL MODE → Git publish skipped"
    fi

  elif [ "$result_code" = "0" ]; then
    echo "⏭️ ${label}: no update → skip final/publish | $(date '+%Y-%m-%d %H:%M:%S')"

  else
    echo "❌ ${label}: watch_odds_updates failed code=${result_code} | $(date '+%Y-%m-%d %H:%M:%S')"
    exit "$result_code"
  fi
}

run_final_check_before_exit() {
  echo "🧹 final check before watch exit | $(date '+%Y-%m-%d %H:%M:%S')"
  set +e
  $PYTHON scripts/public01/car9/watch/watch_odds_updates.py \
    --date "$DATE" \
    --once \
    --final-check
  local result_code=$?
  set -e

  if [ "$result_code" = "0" ] || [ "$result_code" = "2" ]; then
    echo "💰 final-check after all races: build profit summary | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/build_profit_summary.py --date "$DATE"

    echo "📄 final-check after all races: rebuild venue index pages with profit summary | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/build_venue_index_pages.py --date "$DATE"

    echo "📊 final-check after all races: rebuild local profit index | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/build_profit_index.py

    echo "🧱 final-check: snapshot → final | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/build_final_from_snapshot.py --force

    echo "🔄 final-check: local sync → docs/public | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/publish/local_sync.py

    # -----------------------------------
    # 当日分をローカルarchiveへ保存
    # docs/public はGit管理外のローカルテスト環境。
    # Git公開の有無とは切り離して実行する。
    # -----------------------------------
    echo "📦 final-check: local archive | date=$DATE | $(date '+%Y-%m-%d %H:%M:%S')"
    $PYTHON scripts/public01/car9/build/archive_day.py       --date "$DATE"       --force       --skip-no-grade


    if [ "$PUBLIC01_PUBLISH" = "1" ]; then
      echo "🚀 final-check: publish final/archive | $(date '+%Y-%m-%d %H:%M:%S')"
      $PYTHON scripts/public01/car9/publish/git_publish.py         || echo "⚠️ public01 git publish failed, but watch shell continues."
    else
      echo "🧪 final-check: LOCAL MODE → Git publish skipped"
    fi
  else
    publish_if_updated "$result_code" "final-check"
  fi
}

should_stop_after_final_race() {
  $PYTHON - << EOF
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

date = "$DATE"
minutes = int("$FINAL_AUTO_STOP_MINUTES")
path = Path(f"data/public01/car9/watch/public01_car9_odds_term_table_{date}.csv")

if not path.exists():
    print(f"auto-stop skip: term table missing: {path}")
    sys.exit(1)

df = pd.read_csv(path, dtype=str).fillna("")
if df.empty or "post_time" not in df.columns:
    print("auto-stop skip: post_time missing")
    sys.exit(1)

final_dt = None
for value in df["post_time"].astype(str):
    value = value.strip()
    if not value:
        continue
    try:
        dt = datetime.strptime(f"{date} {value}", "%Y-%m-%d %H:%M")
    except Exception:
        continue
    if final_dt is None or dt > final_dt:
        final_dt = dt

if final_dt is None:
    print("auto-stop skip: no valid post_time")
    sys.exit(1)

stop_dt = final_dt + timedelta(minutes=minutes)
now = datetime.now()

if now >= stop_dt:
    print(f"auto-stop ready: final={final_dt.strftime('%H:%M')} stop={stop_dt.strftime('%H:%M')} now={now.strftime('%H:%M')}")
    sys.exit(0)

print(f"auto-stop waiting: final={final_dt.strftime('%H:%M')} stop={stop_dt.strftime('%H:%M')} now={now.strftime('%H:%M')}")
sys.exit(1)
EOF
}

pre_first_pending_file() {
  local venue_id="$1"
  echo "data/public01/car9/watch/.public01_car9_pre_first_refresh_${DATE}_v${venue_id}.pending"
}

is_pre_first_pending() {
  local venue_id="$1"
  local pending_file
  pending_file="$(pre_first_pending_file "$venue_id")"
  [ -f "$pending_file" ]
}

mark_pre_first_pending() {
  local venue_id="$1"
  local pending_file
  mkdir -p data/public01/car9/watch
  pending_file="$(pre_first_pending_file "$venue_id")"
  date +%s > "$pending_file"
}

clear_pre_first_pending() {
  local venue_id="$1"
  local pending_file
  pending_file="$(pre_first_pending_file "$venue_id")"
  rm -f "$pending_file"
}

mark_pre_first_refresh() {
  local venue_id="$1"
  mkdir -p data/public01/car9/watch
  date +%s > \
    "data/public01/car9/watch/.public01_car9_pre_first_refresh_${DATE}_v${venue_id}.ts"

  # 今回の予定更新が完全成功したので再試行状態を解除。
  clear_pre_first_pending "$venue_id"
}

get_pre_first_refresh_venues() {
  $PYTHON - << EOF
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

date = "$DATE"
interval_minutes = int("$PRE_FIRST_REFRESH_INTERVAL_MINUTES")
merge_window_minutes = 15
start_time = datetime.strptime(f"{date} 10:00", "%Y-%m-%d %H:%M")
now = datetime.now()

term = Path(
    f"data/public01/car9/watch/"
    f"public01_car9_odds_term_table_{date}.csv"
)

if not term.exists() or now < start_time:
    sys.exit(0)

df = pd.read_csv(term, dtype=str).fillna("")
required = {"venue_id", "race_no", "post_time", "odds_fetch_time"}

if not required.issubset(df.columns):
    sys.exit(0)

ready = []

for venue_id, sub in df.groupby("venue_id", sort=False):
    first = sub.sort_values(
        "race_no",
        key=lambda x: pd.to_numeric(x, errors="coerce")
    ).iloc[0]

    try:
        first_post = datetime.strptime(
            f"{date} {first['post_time'].strip()}",
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        continue

    # この開催の最初の対象Rが始まったら
    # pre-first更新は終了。
    if now >= first_post:
        continue

    try:
        pre15 = datetime.strptime(
            f"{date} {first['odds_fetch_time'].strip()}",
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        pre15 = first_post - timedelta(minutes=15)

    state = Path(
        f"data/public01/car9/watch/"
        f".public01_car9_pre_first_refresh_{date}_v{venue_id}.ts"
    )

    last_refresh = None
    if state.exists():
        try:
            last_refresh = datetime.fromtimestamp(
                float(state.read_text().strip())
            )
        except Exception:
            last_refresh = None

    # 10:00以降、その開催がまだ一度も更新されていなければ即実行。
    if last_refresh is None:
        ready.append(str(venue_id))
        continue

    regular_due = last_refresh + timedelta(minutes=interval_minutes)

    # 15分前更新をまだ行っていない場合だけ候補にする。
    pre15_pending = pre15 > last_refresh

    # 次の30分更新から15分以内にpre15が来る場合は、
    # 30分更新を省略してpre15へ寄せる。
    if pre15_pending:
        delta = (pre15 - regular_due).total_seconds() / 60

        if 0 <= delta <= merge_window_minutes:
            if now >= pre15:
                ready.append(str(venue_id))
            continue

    # 通常30分更新。
    if now >= regular_due:
        ready.append(str(venue_id))
        continue

    # 30分周期より先にpre15へ到達した場合。
    if pre15_pending and now >= pre15:
        ready.append(str(venue_id))

if ready:
    print(" ".join(ready))
EOF
}

# -----------------------------------
# common 正式9車判定
# 9車 + L1除外 + 外国人含有レース除外
# -----------------------------------
if $PYTHON scripts/common/check_car9_day.py --date "$DATE" --json; then
  HAS_9=1
else
  CAR9_RC=$?

  if [ "$CAR9_RC" = "1" ]; then
    echo "⏭️ no target 9-race → exit watch | $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
  fi

  echo "❌ common 9車判定失敗 | date=$DATE | rc=$CAR9_RC"
  exit "$CAR9_RC"
fi

# publish運用時のみ、既存公開系とのgitタイミング重複を避けるため5分遅らせる
if [ "$PUBLIC01_PUBLISH" = "1" ]; then
  WATCH_START_DELAY_SECONDS=300
  echo "⏳ public01 car9 watch start delay ${WATCH_START_DELAY_SECONDS}s | $(date '+%Y-%m-%d %H:%M:%S')"
  sleep "$WATCH_START_DELAY_SECONDS"
  echo "▶️ public01 car9 watch resumed | $(date '+%Y-%m-%d %H:%M:%S')"
else
  echo "🧪 LOCAL MODE: watch start delay skipped"
fi

while true
do
  NOW=$(date +%H%M)

  # 21:00以降は終了
  if [ "$NOW" -gt 2100 ]; then
    run_final_check_before_exit
    echo "🛑 END public01 car9 watch | $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
  fi

  # 最終9車レース発走 + 20分を過ぎたら、最終確認・収支作成を行って終了
  set +e
  STOP_REASON=$(should_stop_after_final_race)
  STOP_READY=$?
  set -e
  echo "🧭 ${STOP_REASON}"
  if [ "$STOP_READY" = "0" ]; then
    run_final_check_before_exit
    echo "🛑 END public01 car9 watch after final race + ${FINAL_AUTO_STOP_MINUTES}min | $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
  fi

  PRE_FIRST_VENUES="$(get_pre_first_refresh_venues)"
  PRE_FIRST_RAN=0

  if [ -n "$PRE_FIRST_VENUES" ]; then
    for PRE_FIRST_VENUE in $PRE_FIRST_VENUES; do
      echo "🔄 pre-first odds refresh v${PRE_FIRST_VENUE} | $(date '+%Y-%m-%d %H:%M:%S')"

      TERM_TABLE="data/public01/car9/watch/public01_car9_odds_term_table_${DATE}.csv"

      BEFORE_ODDS_UPDATED_AT="$(
        $PYTHON - "$TERM_TABLE" "$PRE_FIRST_VENUE" <<'PY_CHECK'
import sys
import pandas as pd

path, venue_id = sys.argv[1], str(sys.argv[2])

try:
    df = pd.read_csv(path, dtype=str).fillna("")
    if "odds_updated_at" not in df.columns:
        print("")
    else:
        mask = df["venue_id"].astype(str) == venue_id
        values = df.loc[mask, "odds_updated_at"].astype(str)
        values = values[values != ""]
        print(values.max() if len(values) else "")
except Exception:
    print("")
PY_CHECK
      )"

      # .pending がある場合だけ、前回の部分失敗の再試行。
      # .pending がなければ新しい予定更新なので全Rを取得する。
      PRE_FIRST_RETRY_ONLY=0
      if is_pre_first_pending "$PRE_FIRST_VENUE"; then
        PRE_FIRST_RETRY_ONLY=1
      fi

      RETRY_ARGS=()
      if [ "$PRE_FIRST_RETRY_ONLY" = "1" ]; then
        RETRY_ARGS+=(--retry-watching-only)
        echo "🔁 pre-first partial retry v${PRE_FIRST_VENUE}: watching only"
      fi

      set +e
      $PYTHON scripts/public01/car9/watch/watch_odds_updates.py \
        --date "$DATE" \
        --once \
        --initial \
        --venue-id "$PRE_FIRST_VENUE" \
        "${RETRY_ARGS[@]}"
      PRE_FIRST_RESULT=$?
      set -e

      PRE_FIRST_RAN=1

      AFTER_ODDS_UPDATED_AT="$(
        $PYTHON - "$TERM_TABLE" "$PRE_FIRST_VENUE" <<'PY_CHECK'
import sys
import pandas as pd

path, venue_id = sys.argv[1], str(sys.argv[2])

try:
    df = pd.read_csv(path, dtype=str).fillna("")
    if "odds_updated_at" not in df.columns:
        print("")
    else:
        mask = df["venue_id"].astype(str) == venue_id
        values = df.loc[mask, "odds_updated_at"].astype(str)
        values = values[values != ""]
        print(values.max() if len(values) else "")
except Exception:
    print("")
PY_CHECK
      )"

      # odds_updated_at の更新に加えて、
      # 対象会場に watching が残っていない場合だけ今回更新を完了扱いにする。
      PRE_FIRST_WATCHING_COUNT="$(
        $PYTHON - "$TERM_TABLE" "$PRE_FIRST_VENUE" <<'PY_CHECK'
import sys
import pandas as pd

path, venue_id = sys.argv[1], str(sys.argv[2])

try:
    df = pd.read_csv(path, dtype=str).fillna("")
    mask = df["venue_id"].astype(str) == venue_id
    if "odds_status" not in df.columns:
        print(999999)
    else:
        statuses = (
            df.loc[mask, "odds_status"]
            .astype(str)
            .str.lower()
        )
        print(int((statuses == "watching").sum()))
except Exception:
    print(999999)
PY_CHECK
      )"

      # 終了コードではなく、
      # 1) 実際に odds_updated_at が進んだ
      # 2) 会場内に watching が残っていない
      # の両方で成功判定する。
      if [ -n "$AFTER_ODDS_UPDATED_AT" ] &&          [ "$AFTER_ODDS_UPDATED_AT" != "$BEFORE_ODDS_UPDATED_AT" ] &&          [ "$PRE_FIRST_WATCHING_COUNT" = "0" ]; then
        echo "✅ pre-first odds reflected v${PRE_FIRST_VENUE}: ${AFTER_ODDS_UPDATED_AT}"
        mark_pre_first_refresh "$PRE_FIRST_VENUE"
      else
        mark_pre_first_pending "$PRE_FIRST_VENUE"
        echo "⚠️ pre-first odds incomplete v${PRE_FIRST_VENUE} watching=${PRE_FIRST_WATCHING_COUNT} → retry next watch cycle"
      fi

      publish_if_updated         "$PRE_FIRST_RESULT"         "pre-first-refresh-v${PRE_FIRST_VENUE}"
    done
  fi

  # 10:00〜21:00の間だけ通常watchを実行。
  # 同じ周回でpre-first更新を実行した場合は重複実行しない。
  if [ "$NOW" -ge 1000 ] && [ "$NOW" -le 2100 ] && [ "$PRE_FIRST_RAN" = "0" ]; then
    echo "🕒 within time range → run watch_odds_updates | $(date '+%Y-%m-%d %H:%M:%S')"

    set +e
    $PYTHON scripts/public01/car9/watch/watch_odds_updates.py \
      --date "$DATE" \
      --once
    WATCH_RESULT=$?
    set -e

    publish_if_updated "$WATCH_RESULT" "watch"

  else
    echo "⏸ outside time range → sleep"
  fi

  # 1分待機
  sleep 60
done
