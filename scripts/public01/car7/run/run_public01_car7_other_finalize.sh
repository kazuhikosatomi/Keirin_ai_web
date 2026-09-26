#!/bin/bash

set -u

DATE="${1:-$(date '+%Y-%m-%d')}"
PYTHON="${PYTHON:-python3}"

TERM_TABLE="data/public01/car7/watch/public01_car7_odds_term_table_${DATE}.csv"
WATCH_TARGETS="data/public01/car7/config/watch_targets_${DATE}.csv"
FINALIZER="scripts/public01/car7/watch/watch_odds_updates.py"

echo "============================================================"
echo " public01/car7 OTHER finalize runner"
echo " DATE=${DATE}"
echo "============================================================"

if [ ! -f "$TERM_TABLE" ]; then
  echo "⏳ term table not found yet → wait: $TERM_TABLE"

  while [ ! -f "$TERM_TABLE" ]; do
    sleep 60
  done

  echo "✅ term table detected: $TERM_TABLE"
fi

if [ -f "$WATCH_TARGETS" ]; then
  echo "✅ watch targets detected: $WATCH_TARGETS"
else
  echo "ℹ️ watch targets not found → WATCH 0 venues: $WATCH_TARGETS"
fi

if [ ! -f "$FINALIZER" ]; then
  echo "❌ finalizer not found: $FINALIZER"
  exit 1
fi

while true; do
  NOW="$(date '+%H:%M')"

  READY_VENUES="$(
    "$PYTHON" - "$DATE" "$TERM_TABLE" "$WATCH_TARGETS" "$NOW" <<'PY'
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

date, term_path, watch_path, now_hm = sys.argv[1:5]

df = pd.read_csv(term_path, dtype=str).fillna("")

watch_venues = set()
watch_path_obj = Path(watch_path)

if watch_path_obj.exists():
    watch = pd.read_csv(watch_path_obj, dtype=str).fillna("")

    if "venue_id" not in watch.columns:
        raise SystemExit(f"watch targets missing venue_id: {watch_path}")

    watch_venues = set(
        pd.to_numeric(watch["venue_id"], errors="coerce")
          .dropna()
          .astype(int)
    )

df["_venue"] = pd.to_numeric(df["venue_id"], errors="coerce")
df["_race"] = pd.to_numeric(df["race_no"], errors="coerce")

df = df[df["_venue"].notna()].copy()
df["_venue"] = df["_venue"].astype(int)

other = df[~df["_venue"].isin(watch_venues)].copy()

now_dt = datetime.strptime(f"{date} {now_hm}", "%Y-%m-%d %H:%M")

ready = []

for venue, g in other.groupby("_venue"):
    g = g.sort_values("_race")

    if "result_status" not in g.columns:
        all_done = False
    else:
        all_done = (
            g["status"].astype(str).eq("done")
            & g["odds_status"].astype(str).eq("done")
            & g["result_status"].astype(str).eq("done")
        ).all()

    if all_done:
        continue

    last = g.iloc[-1]
    post_time = str(last.get("post_time", "")).strip()

    try:
        post_dt = datetime.strptime(
            f"{date} {post_time}",
            "%Y-%m-%d %H:%M",
        )
    except ValueError:
        continue

    finalize_at = post_dt + timedelta(minutes=20)

    if now_dt >= finalize_at:
        ready.append(int(venue))

for venue in sorted(ready):
    print(venue)
PY
  )"

  if [ -n "$READY_VENUES" ]; then
    while IFS= read -r VENUE; do
      [ -z "$VENUE" ] && continue

      echo
      echo "🏁 OTHER finalize start v${VENUE} | $(date '+%Y-%m-%d %H:%M:%S')"

      "$PYTHON" "$FINALIZER" \
        --date "$DATE" \
        --other-finalize \
        --venue-id "$VENUE"

      RC=$?

      if [ "$RC" -eq 0 ]; then
        echo "✅ OTHER finalize completed v${VENUE}"

        # この開催場のOTHER最終処理完了時刻をterm tableへ保存する。
        "$PYTHON" - "$TERM_TABLE" "$VENUE" <<'PYTIME'
import sys
from datetime import datetime

import pandas as pd

term_path, venue = sys.argv[1:3]

df = pd.read_csv(term_path, dtype=str).fillna("")

venue_num = int(float(venue))
venue_col = pd.to_numeric(df["venue_id"], errors="coerce")

if "other_finalize_time" not in df.columns:
    df["other_finalize_time"] = ""

finalize_time = datetime.now().strftime("%H:%M")

mask = venue_col.eq(venue_num)
df.loc[mask, "other_finalize_time"] = finalize_time

df.to_csv(term_path, index=False)

print(
    f"🕒 OTHER finalize time saved: "
    f"v{venue_num:02d} {finalize_time}"
)
PYTIME

        echo "🪄 OTHER finalize: build final snapshot | $(date '+%Y-%m-%d %H:%M:%S')"
        "$PYTHON" scripts/public01/car7/build/build_final_from_snapshot.py --force

        echo "📁 OTHER finalize: local sync | $(date '+%Y-%m-%d %H:%M:%S')"
        "$PYTHON" scripts/public01/car7/publish/local_sync.py           --date "$DATE"

        echo "🗂️ OTHER finalize: archive update | $(date '+%Y-%m-%d %H:%M:%S')"
        "$PYTHON" scripts/public01/car7/build/archive_day.py --date "$DATE" --force

        if [ "${PUBLIC01_PUBLISH:-0}" = "1" ]; then
          echo "🚀 OTHER finalize: git publish | $(date '+%Y-%m-%d %H:%M:%S')"
          "$PYTHON" scripts/public01/car7/publish/git_publish.py
        else
          echo "🧪 OTHER finalize: LOCAL MODE → Git publish skipped"
        fi
      else
        echo "⚠️ OTHER finalize incomplete v${VENUE} rc=${RC} → retry next cycle"
      fi
    done <<< "$READY_VENUES"
  fi

  REMAINING="$(
    "$PYTHON" - "$TERM_TABLE" "$WATCH_TARGETS" <<'PY'
import sys
from pathlib import Path

import pandas as pd

term_path, watch_path = sys.argv[1:3]

df = pd.read_csv(term_path, dtype=str).fillna("")

watch_venues = set()
watch_path_obj = Path(watch_path)

if watch_path_obj.exists():
    watch = pd.read_csv(watch_path_obj, dtype=str).fillna("")

    if "venue_id" not in watch.columns:
        raise SystemExit(f"watch targets missing venue_id: {watch_path}")

    watch_venues = set(
        pd.to_numeric(watch["venue_id"], errors="coerce")
          .dropna()
          .astype(int)
    )

df["_venue"] = pd.to_numeric(df["venue_id"], errors="coerce")
df = df[df["_venue"].notna()].copy()
df["_venue"] = df["_venue"].astype(int)

other = df[~df["_venue"].isin(watch_venues)]

remaining = 0

for _, g in other.groupby("_venue"):
    if "result_status" not in g.columns:
        all_done = False
    else:
        all_done = (
            g["status"].astype(str).eq("done")
            & g["odds_status"].astype(str).eq("done")
            & g["result_status"].astype(str).eq("done")
        ).all()

    if not all_done:
        remaining += 1

print(remaining)
PY
  )"

  if [ "$REMAINING" = "0" ]; then
    echo
    echo "✅ all OTHER venues completed | $(date '+%Y-%m-%d %H:%M:%S')"
    exit 0
  fi

  echo "⏳ OTHER remaining venues=${REMAINING} | now=${NOW}"
  sleep 60
done
