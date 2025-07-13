import argparse
import pandas as pd
from bs4 import BeautifulSoup
import time
import sys
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

parser = argparse.ArgumentParser()
parser.add_argument("--target", help="対象日付 (YYYY-MM-DD)")
args = parser.parse_args()

if args.target:
    start_date = end_date = args.target
else:
    yesterday = datetime.now() - timedelta(days=1)
    start_date = end_date = yesterday.strftime("%Y-%m-%d")

# スクリプト開始ログ
print("==================== scrape_results_headless_yesterday.py START ====================")
print(f"📅 対象日: {start_date}")

try:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
except ValueError:
    print("日付形式が正しくありません（YYYY-MM-DD）")
    sys.exit(1)

# ✅ ファイル読込
import os
from dotenv import load_dotenv
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
calendar_df = pd.read_csv(os.path.join(script_dir, "../../data/calendar/calendar_all.csv"))  # ← 開催カレンダー
# 日付カラムを正規化（YYYY-MM-DD形式へ変換）
calendar_df["date"] = pd.to_datetime(calendar_df["date"].astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")
jyocode_path = os.path.join(script_dir, "../../data/master/venue_master.csv")
jyocode_df = pd.read_csv(jyocode_path)  # ← 場コード対応表

player_path = os.path.join(script_dir, "../../data/master/player_master.csv")
player_df = pd.read_csv(player_path)

# ✅ Chrome起動
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

# ✅ 日付ループ
current = start_dt
while current <= end_dt:
    open_day = current.strftime("%Y-%m-%d")
    print(f"🔍 {open_day} のレース結果を取得中...")

    # ⬇ カレンダーと突合し、この日に開催の競輪場だけ取得
    day_venues = calendar_df[calendar_df["date"] == open_day]
    merged = pd.merge(day_venues, jyocode_df, on="venue_name", how="inner")
    venues = [(str(row.venue_id_y).zfill(2), row.venue_name) for row in merged.itertuples(index=False)]

    all_results = []

    for jyo_code, jyo_name in venues:
        url = f"https://www.chariloto.com/keirin/results/{jyo_code}/{open_day}"
        driver.get(url)
        print(f"🌐 リクエスト送信: {url}")
        time.sleep(10)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        print(f"📥 レスポンス受信: ページ長 = {len(driver.page_source)}")
        loop_blocks = [t for t in soup.find_all("table", class_="table") if "周回予想" in t.get_text()]
        result_tables = [t for t in soup.find_all("table") if "着" in t.get_text() and "選手名" in t.get_text()]

        if not loop_blocks or not result_tables:
            print(f"⚠️ {jyo_name}: レース情報なし (loop_blocks: {len(loop_blocks)}, result_tables: {len(result_tables)})")
            with open(f"debug_{open_day}_{jyo_code}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            continue

        for race_num, (result_table, loop_table) in enumerate(zip(result_tables, loop_blocks), start=1):
            spans = loop_table.find_all("span")
            lines = []
            current_line = []
            for span in spans:
                if "square" in span.get("class", []):
                    current_line.append(span.text.strip())
                elif "p10" in span.get("class", []):
                    if current_line:
                        lines.append(current_line)
                        current_line = []
            if current_line:
                lines.append(current_line)

            line_df = []
            for line_id, line in enumerate(lines, 1):
                for pos, car in enumerate(line, 1):
                    line_df.append({"車番": car, "line_id": line_id, "line_pos": pos})
            df_line = pd.DataFrame(line_df)

            records = []
            for tr in result_table.find_all("tr")[1:]:
                td = tr.find_all("td")
                if len(td) < 8:
                    continue
                sb_text = td[10].text.strip() if len(td) > 10 else ""
                records.append({
                    "日付": open_day,
                    "レース場": jyo_name,
                    "場コード": jyo_code,
                    "レース": f"{race_num}R",
                    "順位": td[0].text.strip(),
                    "車番": td[1].text.strip(),
                    "選手名": td[2].text.strip(),
                    "年齢": td[3].text.strip(),
                    "府県": td[4].text.strip(),
                    "級班": td[6].text.strip(),
                    "着差": td[7].text.strip(),
                    "上り": td[8].text.strip() if len(td) > 8 else "",
                    "決まり手": td[9].text.strip() if len(td) > 9 else "",
                    "S": "S" if "S" in sb_text else "",
                    "B": "B" if "B" in sb_text else "",
                })

            df_result = pd.DataFrame(records)
            df_merged = pd.merge(df_result, df_line, on="車番", how="left")

            # スペース削除用の関数
            def normalize_name(name):
                return name.replace(" ", "").replace("　", "").strip()

            # 5文字までの短縮名生成（突合用）
            def short_key(name):
                return normalize_name(name)[:5]

            # 正規化した短縮キーで突合
            df_merged["short_name"] = df_merged["選手名"].apply(short_key)
            player_df["short_name"] = player_df["name_kanji"].apply(short_key)

            df_merged = pd.merge(df_merged, player_df[["racer_id", "short_name"]], on="short_name", how="left")

            # name_kanjiはオリジナルを保持
            df_merged["name_kanji"] = df_merged["選手名"]

            all_results.append(df_merged)

            time.sleep(0.3)

    # ✅ 日付ごとのCSV保存
    if all_results:
        df_final = pd.concat(all_results, ignore_index=True)
        df_final = df_final.rename(columns={
            "日付": "date",
            "レース場": "venue_name",
            "場コード": "venue_id",
            "レース": "race_no",
            "順位": "rank",
            "車番": "car_no",
            "年齢": "age",
            "府県": "prefecture",
            "級班": "grade",
            "着差": "margin",
            "上り": "last_time",
            "決まり手": "finish_tactics",
            "S": "s_mark",
            "B": "b_mark"
        })

        df_final["race_no"] = df_final["race_no"].str.replace("R", "").astype("Int64")
        tactics_map = {"逃げ": "逃", "マーク": "マ", "差し": "差", "捲くり": "捲"}
        df_final["finish_tactics"] = df_final["finish_tactics"].map(tactics_map).fillna(df_final["finish_tactics"])

        columns_order = [
            "date", "venue_name", "venue_id", "race_no", "rank", "car_no",
            "name_kanji", "racer_id", "age", "prefecture", "grade", "margin", "last_time",
            "finish_tactics", "s_mark", "b_mark", "line_id", "line_pos"
        ]
        df_final = df_final[columns_order]

        year = open_day[:4]
        output_dir = os.path.join(script_dir, f"../../data/results/{year}")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"results_{open_day}.csv")
        df_final.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"🎯 出力件数: {len(df_final)}")
        print(f"✅ 保存完了: {output_path}")
        print(f"📦 ファイルサイズ: {os.path.getsize(output_path)} bytes")
    else:
        print(f"❌ {open_day}: データ取得なし")

    current += timedelta(days=1)

driver.quit()
print("🎉 すべての期間の処理が完了しました。")
