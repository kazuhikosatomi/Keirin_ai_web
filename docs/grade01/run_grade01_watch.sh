#!/bin/bash

# 仮想環境有効化
source /Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/activate

# 念のためプロジェクトルートへ移動
cd /Users/satomi/keirin/GitHub/keirin_ai_web

DATE=${1:-$(date +%Y-%m-%d)}
export PYTHON="/Users/satomi/keirin/GitHub/keirin_ai_web/venv/bin/python"

echo "========================================"
echo "👀 START grade01 watch | $DATE"
echo "========================================"

# -----------------------------------
# 9車チェック（なければ即終了）
# -----------------------------------
HAS_9=$($PYTHON - << EOF
import pandas as pd, os

date="$DATE"
path=f"data/entries/{date[:4]}/entry_{date}.csv"

if not os.path.exists(path):
    print(0)
    exit()

df=pd.read_csv(path)
if df.empty:
    print(0)
    exit()

print(1 if df["car_no"].max()==9 else 0)
EOF
)

if [ "$HAS_9" != "1" ]; then
  echo "⏭️ no 9-race → exit watch"
  exit 0
fi

while true
do
  NOW=$(date +%H%M)

  # 21:00以降は終了
  if [ "$NOW" -gt 2100 ]; then
    echo "🛑 end watch"
    exit 0
  fi

  # 10:00〜21:00の間だけ実行
  if [ "$NOW" -ge 1000 ] && [ "$NOW" -le 2100 ]; then
    echo "🕒 within time range → run step06"

    $PYTHON scripts/grade01/grade01_step06_watch_odds_updates.py \
      --date "$DATE" \
      --once

  else
    echo "⏸ outside time range → sleep"
  fi

  # 1分待機
  sleep 60
done