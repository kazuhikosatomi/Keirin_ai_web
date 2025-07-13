import requests
from bs4 import BeautifulSoup
import csv
import time
import unicodedata

# === 変換設定 ===
grade_map = {"Ｇ１": "G1", "Ｇ２": "G2", "Ｇ３": "G3", "Ｆ１": "F1", "Ｆ２": "F2", "ＧＰ": "GP"}
indicator_map = {"２連対率": "2連対率", "３連対率": "3連対率"}  # 全角数字の修正
section_map = {"~1昨年": "～１昨年", "～1昨年": "～１昨年"}  # 表記ぶれ対応

# === 固定列構成 ===
sections = ["～１昨年", "昨年", "本年", "通算"]
grades = ["合計", "F2", "F1", "G3", "G2", "G1", "GP"]
indicators = ["出走数", "優勝", "1着", "2着", "3着", "着外", "棄権", "失格", "勝率", "2連対率", "3連対率"]

profile_fields = ["name", "furigana", "prefecture", "birthdate", "age", "gender", "snum", "term", "rank", "style", "score"]
stats_fields = [f"{sec}_{gr}_{ind}" for sec in sections for gr in grades for ind in indicators]
fieldnames = profile_fields + stats_fields

# === ヘルパー関数 ===
def clean(text):
    return unicodedata.normalize("NFKC", text.strip().replace('\u3000', ' '))

def normalize_section(s):
    return section_map.get(s, clean(s))

def normalize_grade(g):
    g = clean(g)
    return grade_map.get(g, g)

def normalize_indicator(i):
    return indicator_map.get(i, i)

# === データ取得関数 ===
def fetch_combined_player_data(snum):
    url = f"https://keirin.jp/pc/racerprofile?snum={snum:06d}"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        if len(tables) < 3:
            print(f"❌ 該当なし or 不完全: {snum:06d}")
            return None

        # プロフィール
        base_info = [clean(td.text) for td in tables[2].find_all("tr")[1].find_all("td")]
        advanced_info = [clean(td.text) for td in tables[2].find_all("tr")[3].find_all("td")]

        data = dict.fromkeys(fieldnames, "")  # 初期化
        data.update({
            "name": base_info[0],
            "furigana": base_info[1],
            "prefecture": base_info[2],
            "birthdate": base_info[3],
            "age": base_info[4],
            "gender": base_info[5],
            "snum": base_info[6],
            "term": advanced_info[0],
            "rank": advanced_info[1],
            "style": advanced_info[4],
            "score": advanced_info[5],
        })

        # 成績テーブルの特定
        stats_table = None
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) >= 2 and ("～１昨年" in rows[1].text or "通算" in rows[1].text):
                stats_table = table
                break

        if stats_table:
            rows = stats_table.find_all("tr")
            headers = [normalize_indicator(clean(td.text)) for td in rows[0].find_all("td")][1:]
            current_section = None

            for row in rows[1:]:
                cols = [clean(td.text) for td in row.find_all("td")]
                if len(cols) < 2:
                    continue

                first = cols[0]
                second = cols[1]

                if second == "合計":
                    current_section = normalize_section(first)
                    grade = "合計"
                    values = cols[2:]
                elif current_section:
                    grade = normalize_grade(first)
                    values = cols[1:]
                else:
                    continue

                for i, value in enumerate(values):
                    if i < len(headers):
                        indicator = headers[i]
                        key = f"{current_section}_{grade}_{indicator}"
                        if key in data:
                            data[key] = value
                        else:
                            print(f"⚠️ 未知キー: {key} → 値: {value}")  # デバッグ用

        else:
            print(f"📭 {snum:06d}: 成績テーブルが見つかりません")

        return data

    except Exception as e:
        print(f"⚠️ エラー（{snum:06d}）: {e}")
        return None

# === CSV出力 ===
csv_file = "player_combined.csv"
with open(csv_file, "w", newline='', encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for snum in range(13100, 13120 + 1):  # 範囲は必要に応じて調整
        player_data = fetch_combined_player_data(snum)
        if player_data:
            writer.writerow(player_data)
            print(f"✅ 取得成功: {snum:06d} → {player_data['name']}")
        else:
            print(f"❌ 該当なし or データ不備: {snum:06d}")
        time.sleep(0.5)

print(f"📦 統合CSV保存完了 → {csv_file}")