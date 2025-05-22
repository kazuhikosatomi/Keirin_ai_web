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

try:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
except ValueError:
    print("日付形式が正しくありません（YYYY-MM-DD）")
    sys.exit(1)

# ✅ ファイル読込
calendar_df = pd.read_csv("data/calendar/keirin_calendar_2024-12_to_2025-06.csv")  # ← 開催カレンダー
jyocode_df = pd.read_csv("data/venue/jyocode.csv")  # ← 場コード対応表
calendar_df.rename(columns={"place": "競輪場名"}, inplace=True)

# ✅ Chrome起動
chromedriver_path = "/Users/satomi/Desktop/ai/chromedriver-mac-arm64/chromedriver"
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)

# ✅ 日付ループ
current = start_dt
while current <= end_dt:
    open_day = current.strftime("%Y-%m-%d")
    print(f"🔍 {open_day} のレース結果を取得中...")

    # ⬇ カレンダーと突合し、この日に開催の競輪場だけ取得
    day_venues = calendar_df[calendar_df["date"] == open_day]
    merged = pd.merge(day_venues, jyocode_df, on="競輪場名", how="inner")
    venues = [(str(row.Code).zfill(2), row.競輪場名) for row in merged.itertuples(index=False)]

    all_results = []

    for jyo_code, jyo_name in venues:
        url = f"https://www.chariloto.com/keirin/results/{jyo_code}/{open_day}"
        driver.get(url)
        time.sleep(10)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        loop_blocks = [t for t in soup.find_all("table", class_="table") if "周回予想" in t.get_text()]
        result_tables = [t for t in soup.find_all("table") if "着" in t.get_text() and "選手名" in t.get_text()]

        if not loop_blocks or not result_tables:
            print(f"⚠️ {jyo_name}: レース情報なし")
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
            all_results.append(df_merged)

            time.sleep(0.3)

    # ✅ 日付ごとのCSV保存
    if all_results:
        df_final = pd.concat(all_results, ignore_index=True)
        filename = f"chariloto_results_{open_day}.csv"
        df_final.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"✅ 保存完了: {filename}")
    else:
        print(f"❌ {open_day}: データ取得なし")

    current += timedelta(days=1)

driver.quit()
print("🎉 すべての期間の処理が完了しました。")
