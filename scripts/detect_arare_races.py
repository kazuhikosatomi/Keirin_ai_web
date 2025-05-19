import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# 🔸 utils/ ディレクトリをモジュール検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))

from entry_parser import fetch_entry_data
from araredo_calc import calc_araredo
import duckdb

# DuckDB接続
con = duckdb.connect(str(Path(__file__).resolve().parent.parent / "db/keirin_ai.duckdb"))

# カレンダー読み込み
calendar_path = Path(__file__).resolve().parent.parent / "data/calendar/keirin_calendar_2024-12_to_2025-06.csv"
calendar_df = pd.read_csv(calendar_path)
print("calendar_df columns:", calendar_df.columns.tolist())

# 競輪場コード対応表の読み込みと結合
venue_map_path = Path(__file__).resolve().parent.parent / "data/venue/jyocode.csv"
venue_df = pd.read_csv(venue_map_path)
print("venue_df columns:", venue_df.columns.tolist())
calendar_df = calendar_df.merge(venue_df, left_on="place", right_on="競輪場名", how="left")


# 固定日（テスト用）
target_dates = ["2025-02-01"]
target_df = calendar_df[calendar_df["date"].isin(target_dates)]

# 結果格納用
result_rows = []

for _, row in target_df.iterrows():
    date = row["date"].replace("-", "")
    venue_id = row["Code"]
    place = row["place"]
    for race in range(1, 13):
        try:
            query = f"""
                WITH odds_filtered AS (
                  SELECT date, venue_id, race_no, odds1
                  FROM odds
                  WHERE bet_code = 3
                    AND date = {date}
                    AND venue_id = {venue_id}
                    AND race_no = {race}
                ),
                agg AS (
                  SELECT MIN(odds1) AS lowest_odds,
                         MEDIAN(odds1) AS median_odds,
                         SUM(odds1) AS total_sum
                  FROM odds_filtered
                ),
                top3 AS (
                  SELECT SUM(odds1) AS top3_sum
                  FROM (
                    SELECT odds1 FROM odds_filtered ORDER BY odds1 ASC LIMIT 3
                  )
                )
                SELECT agg.lowest_odds, agg.median_odds,
                       ROUND(top3.top3_sum / agg.total_sum, 5) AS top3_ratio
                FROM agg, top3;
            """
            r = con.execute(query).fetchone()
            if r and r[0] is not None:
                lowest_odds, median_odds, top3_ratio = r
                score = calc_araredo(lowest_odds, median_odds, top3_ratio)
                if score >= 50:
                    result_rows.append({
                        "開催日": row["date"],
                        "競輪場": place,
                        "場コード": venue_id,
                        "R": race,
                        "スコア": score
                    })
        except Exception as e:
            print(f"[ERROR] {date} {venue_id}R{race}: {e}")
            continue

# 結果出力
if result_rows:
    df = pd.DataFrame(result_rows)
    print(df)
else:
    print("⚠️ 荒れ度スコア70以上のレースは見つかりませんでした。")