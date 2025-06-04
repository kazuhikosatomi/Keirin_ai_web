import re
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def extract_lineinfo_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    line_groups = []
    current_group = []

    square_tags = soup.select("div.g-flex span")
    for tag in square_tags:
        if "square" in tag.get("class", []):
            try:
                car_number = int(tag.get_text(strip=True))
                current_group.append(car_number)
            except ValueError:
                continue
        elif "p10" in tag.get("class", []):
            if current_group:
                line_groups.append(current_group)
                current_group = []

    if current_group:
        line_groups.append(current_group)

    line_map = {}
    for line_id, group in enumerate(line_groups, start=1):
        for line_pos, car_number in enumerate(group, start=1):
            line_map[str(car_number)] = {
                "line_id": line_id,
                "line_pos": line_pos
            }

    return line_map

def extract_result_pairs(text):
    # 成績欄から「初3準1」→ ['初3', '準1'] のように分割
    return re.findall(r"[^\d\s]+\d+", text)[:5] + [""] * (5 - len(re.findall(r"[^\d\s]+\d+", text)))

def fetch_entry_data(url):
    print("✅ fetch_entry_data() 開始")
    print("🔗 URL:", url)
    try:
        match = re.search(r"/athletes/(\d{4}-\d{2}-\d{2})/(\d+)/(\d+)", url)
        if not match:
            return {"error": "URL形式が正しくありません"}

        date_str, place_code, race_num = match.groups()

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//th[contains(text(), '選手名')]"))
            )
        except TimeoutException:
            html = driver.page_source
            save_path = os.path.abspath("entry_page_debug_on_error.html")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"❌ WebDriverWaitで失敗。取得HTMLを保存しました: {save_path}")
            return {"error": "タイムアウトエラー"}

        html = driver.page_source
        if not html:
            print("❌ HTMLが空です")
            return {"error": "HTMLが取得できませんでした"}
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")
        print("🧪 BeautifulSoup による HTML パース完了")
        line_map = extract_lineinfo_from_html(html)

        tables = soup.find_all("table")
        target_table = None
        for table in tables:
            if "選手名" in table.get_text():
                target_table = table
                break

        if not target_table:
            return {"error": "選手テーブルが見つかりませんでした"}

        rows = target_table.select("tbody tr")
        print("👥 抽出した行数（選手行）:", len(rows))
        data = []
        prev_frame = ""
        for row in rows:
            tds = row.find_all(["td", "th"])
            # 柔軟な判定に変更（car_numberが取れるかで判断）
            if len(tds) < 20:
                continue

            if len(tds) >= 34:
                frame_number = tds[1].get_text(strip=True)
                tds_offset = 0
                prev_frame = frame_number
            else:
                frame_number = prev_frame
                tds_offset = -1

            try:
                car_number = tds[2 + tds_offset].get_text(strip=True)
                name = tds[3 + tds_offset].get_text(strip=True)
                age = tds[4 + tds_offset].get_text(strip=True)
                prefecture = tds[5 + tds_offset].get_text(strip=True)
                term = tds[6 + tds_offset].get_text(strip=True)
                grade = tds[7 + tds_offset].get_text(strip=True)
                leg_type = tds[8 + tds_offset].get_text(strip=True)
                gear = tds[9 + tds_offset].get_text(strip=True)
                score = tds[10 + tds_offset].get_text(strip=True)
                first_places = tds[11 + tds_offset].get_text(strip=True)
                second_places = tds[12 + tds_offset].get_text(strip=True)
                third_places = tds[13 + tds_offset].get_text(strip=True)
                outs = tds[14 + tds_offset].get_text(strip=True)
                win_rate = tds[15 + tds_offset].get_text(strip=True)
                top2_rate = tds[16 + tds_offset].get_text(strip=True)
                top3_rate = tds[17 + tds_offset].get_text(strip=True)
                style_escape = tds[18 + tds_offset].get_text(strip=True)
                style_sprint = tds[19 + tds_offset].get_text(strip=True)
                style_chase = tds[20 + tds_offset].get_text(strip=True)
                style_other = tds[21 + tds_offset].get_text(strip=True)
                start_number = tds[22 + tds_offset].get_text(strip=True)
                back_number = tds[23 + tds_offset].get_text(strip=True)
                recent_place1 = tds[24 + tds_offset].get_text(strip=True)
                recent_date1 = tds[25 + tds_offset].get_text(strip=True)
                recent_result1_raw = tds[26 + tds_offset].get_text(strip=True)
                recent_place2 = tds[27 + tds_offset].get_text(strip=True)
                recent_date2 = tds[28 + tds_offset].get_text(strip=True)
                recent_result2_raw = tds[29 + tds_offset].get_text(strip=True)
                recent_place3 = tds[30 + tds_offset].get_text(strip=True)
                recent_date3 = tds[31 + tds_offset].get_text(strip=True)
                recent_result3_raw = tds[32 + tds_offset].get_text(strip=True)
                comment = tds[33 + tds_offset].get_text(strip=True)
            except IndexError:
                continue

            if not car_number:
                continue
                continue

            line_info = line_map.get(car_number, {"line_id": None, "line_pos": None})

            r1 = extract_result_pairs(recent_result1_raw)
            r2 = extract_result_pairs(recent_result2_raw)
            r3 = extract_result_pairs(recent_result3_raw)

            data.append({
                "date": date_str,
                "place_code": place_code,
                "race_num": race_num,
                "frame_number": frame_number,
                "car_number": car_number,
                "name": name,
                "age": age,
                "prefecture": prefecture,
                "term": term,
                "grade": grade,
                "leg_type": leg_type,
                "gear": gear,
                "score": score,
                "first_places": first_places,
                "second_places": second_places,
                "third_places": third_places,
                "outs": outs,
                "win_rate": win_rate,
                "top2_rate": top2_rate,
                "top3_rate": top3_rate,
                "style_escape": style_escape,
                "style_sprint": style_sprint,
                "style_chase": style_chase,
                "style_other": style_other,
                "start_number": start_number,
                "back_number": back_number,
                "recent_place1": recent_place1,
                "recent_date1": recent_date1,
                **{f"recent_race1_{i+1}": r1[i] for i in range(5)},
                "recent_place2": recent_place2,
                "recent_date2": recent_date2,
                **{f"recent_race2_{i+1}": r2[i] for i in range(5)},
                "recent_place3": recent_place3,
                "recent_date3": recent_date3,
                **{f"recent_race3_{i+1}": r3[i] for i in range(5)},
                "comment": comment,
                "line_id": line_info["line_id"],
                "line_pos": line_info["line_pos"]
            })
        # 欠損している recent_raceX_Y キーを文字列 "nan" で補完
        for row in data:
            for prefix in ["recent_race1_", "recent_race2_", "recent_race3_"]:
                for i in range(1, 6):
                    key = f"{prefix}{i}"
                    if key not in row:
                        row[key] = "nan"
        print("📦 登録選手数:", len(data))

        # --- If you have a section that creates a pandas DataFrame and writes CSV, insert below before export or return ---
        # Example (add this block before final return df or CSV export):
        # # Ensure all recent_race columns are string type
        # recent_race_cols = [col for col in df.columns if col.startswith("recent_race")]
        # df[recent_race_cols] = df[recent_race_cols].astype(str)

        # If you prepare a DataFrame here and write to CSV, ensure recent_race columns are string type:
        # For example:
        # import pandas as pd
        # df = pd.DataFrame(data)
        # # Convert all recent_race columns to string type to avoid float64 with NaN
        # recent_cols = [col for col in df.columns if col.startswith("recent_race")]
        # df[recent_cols] = df[recent_cols].fillna("").astype(str)
        # df.to_csv("your_output.csv", index=False)

        import pandas as pd
        df = pd.DataFrame(data)
        # Do not replace NaN values here; keep them as empty and modify CSV afterward
        recent_cols = [col for col in df.columns if col.startswith("recent_race")]
        df[recent_cols] = df[recent_cols].astype(str)
        output_path = f"data/entries/{date_str[:4]}/entry_{date_str}.csv"
        df.to_csv(output_path, index=False)

        # Post-process CSV file to replace empty recent_race fields with "nan"
        import csv
        with open(output_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
        header = reader[0]
        recent_race_indices = [i for i, col in enumerate(header) if col.startswith("recent_race")]

        for row in reader[1:]:
            for i in recent_race_indices:
                if row[i].strip() == "":
                    row[i] = "nan"

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(reader)
        print(f"✅ Post-processed empty recent_race fields to 'nan': {output_path}")
        print(f"✅ Saved: {len(df)} races → {output_path}")
        return {
            "status": "OK",
            "entries": df.to_dict(orient="records"),
            "meta": {
                "date": date_str,
                "place_code": place_code,
                "race_num": race_num
            }
        }
    except Exception as e:
        html = driver.page_source
        save_path = os.path.abspath("entry_page_debug_on_error.html")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"❌ WebDriverWaitで失敗。取得HTMLを保存しました: {save_path}")
        return {"error": str(e)}
