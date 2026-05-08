#!/bin/bash

DATE=${1:-$(date +%Y-%m-%d)}

echo "========================================"
echo "🚀 START grade01 morning | $DATE"
echo "========================================"

# -----------------------------------
# 9車チェック
# -----------------------------------
HAS_9=$(python3 - << EOF
import pandas as pd
import os

date="$DATE"
path=f"data/entries/{date[:4]}/entry_{date}.csv"

if not os.path.exists(path):
    print(0)
    exit()

df=pd.read_csv(path)
if df.empty:
    print(0)
    exit()

print(1 if df["car_no"].max() == 9 else 0)
EOF
)

# -----------------------------------
# 9車なし → step00
# -----------------------------------
if [ "$HAS_9" != "1" ]; then
  echo "⏭️ 9車なし → no grade today page 生成"

  python3 scripts/grade01/grade01_step00_generate_no_grade_today.py --date "$DATE"

  python3 scripts/grade01/grade01_step08_git_publish.py

  echo "========================================"
  echo "🎉 END grade01 morning (no grade)"
  echo "========================================"

  exit 0
fi

# -----------------------------------
# 9車あり → 通常処理
# -----------------------------------
echo "✅ 9車あり → grade01実行"

# step05 タームテーブル
python3 scripts/grade01/grade01_step05_build_odds_term_table.py --date $DATE

# step03 レースHTML生成
python3 scripts/grade01/grade01_step03_generate_all_race_html.py --date $DATE

# step02 today生成
python3 scripts/grade01/grade01_step02_generate_today_html.py --date $DATE

# GitHub反映
python3 scripts/grade01/grade01_step08_git_publish.py

echo "========================================"
echo "🎉 END grade01 morning"
echo "========================================"