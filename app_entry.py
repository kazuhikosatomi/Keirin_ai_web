from flask import Flask, render_template, request
import pandas as pd
import os

app = Flask(__name__)

# 🚫 以下の DuckDB 取得処理は今後も保持すること（消さないこと）🚫
# import gdown
# GOOGLE_FILE_ID = "17_O_DDKSqIl7ubluncZvtrMxeOLsAVSI"
# OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "db", "keirin_data.duckdb")
# if not os.path.exists(OUTPUT_PATH):
#     print("⬇️ Downloading .duckdb file from Google Drive...")
#     url = f"https://drive.google.com/uc?id={GOOGLE_FILE_ID}"
#     os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
#     gdown.download(url, OUTPUT_PATH, quiet=False)

ENTRY_CSV_PATH = "data/entries/2025/entry_2025-06-01.csv"

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    venues = []
    selected_venue = None
    selected_race = None

    if request.method == "POST":
        date = request.form["date"]
        selected_venue = request.form["venue_id"]
        selected_race = request.form["race"]

        if not os.path.exists(ENTRY_CSV_PATH):
            result = {"error": f"CSVが見つかりません: {ENTRY_CSV_PATH}"}
            return render_template("index.html", result=result, venues=[], today=date)

        df = pd.read_csv(ENTRY_CSV_PATH, dtype=str)

        filtered = df[(df["date"] == date) & (df["venue_id"] == selected_venue) & (df["race_no"] == selected_race)]

        if filtered.empty:
            result = {"error": "該当する出走表データがありません。"}
        else:
            entries = []
            for _, row in filtered.iterrows():
                entries.append({
                    "frame_number": row.get("frame_no"),
                    "car_number": row.get("car_no"),
                    "name": row.get("name_kanji"),
                    "age": row.get("age"),
                    "prefecture": row.get("prefecture"),
                    "term": row.get("term"),
                    "grade": row.get("grade"),
                    "leg_type": row.get("style"),
                    "gear": row.get("gear"),
                    "score": row.get("score"),
                    "first_places": row.get("first_places"),
                    "second_places": row.get("second_places"),
                    "third_places": row.get("third_places"),
                    "outs": row.get("outs"),
                    "win_rate": row.get("win_rate"),
                    "top2_rate": row.get("top2_rate"),
                    "top3_rate": row.get("top3_rate"),
                    "style_escape": row.get("style_escape"),
                    "style_sprint": row.get("style_sprint"),
                    "style_chase": row.get("style_chase"),
                    "style_other": row.get("style_other"),
                    "start_number": row.get("start_number"),
                    "back_number": row.get("back_number"),
                    "line_id": row.get("line_id"),
                    "line_pos": row.get("line_pos")
                })

            result = {"entries": entries, "meta": {"date": date, "place_code": selected_venue, "race_num": selected_race}}

    # 会場リストだけは全データから抽出
    if os.path.exists(ENTRY_CSV_PATH):
        try:
            all_df = pd.read_csv(ENTRY_CSV_PATH, dtype=str)
            all_df["venue_id"] = all_df["venue_id"].str.strip().str.zfill(2)
            venues_df = all_df[["venue_id"]].drop_duplicates()

            VENUE_NAME_MAP = {
                "11": "函館", "12": "青森", "13": "いわき平", "21": "弥彦", "22": "前橋", "23": "取手", "24": "宇都宮",
                "25": "大宮", "26": "西武園", "27": "京王閣", "28": "立川", "31": "松戸", "32": "千葉", "34": "川崎",
                "35": "平塚", "36": "小田原", "37": "伊東", "38": "静岡", "42": "名古屋", "43": "岐阜", "44": "大垣",
                "45": "豊橋", "46": "富山", "47": "松阪", "48": "四日市", "51": "福井", "53": "奈良", "54": "向日町",
                "55": "和歌山", "56": "岸和田", "61": "玉野", "62": "広島", "63": "防府", "71": "高松", "73": "小松島",
                "74": "高知", "75": "松山", "81": "小倉", "83": "久留米", "84": "武雄", "85": "佐世保", "86": "別府", "87": "熊本"
            }

            venues = []
            for vid in venues_df["venue_id"]:
                venues.append({
                    "venue_id": vid,
                    "venue_name": VENUE_NAME_MAP.get(vid, f"会場{vid}")
                })
        except Exception:
            venues = []

    return render_template("index.html", result=result, venues=venues, today="2025-06-01", selected_venue=selected_venue, selected_race=selected_race)

if __name__ == "__main__":
    app.run(debug=False, port=5050)
VENUE_NAME_MAP = {
    "11": "函館",
    "12": "青森",
    "13": "いわき平",
    "21": "弥彦",
    "22": "前橋",
    "23": "取手",
    "24": "宇都宮",
    "25": "大宮",
    "26": "西武園",
    "27": "京王閣",
    "28": "立川",
    "31": "松戸",
    "32": "千葉",
    "34": "川崎",
    "35": "平塚",
    "36": "小田原",
    "37": "伊東",
    "38": "静岡",
    "42": "名古屋",
    "43": "岐阜",
    "44": "大垣",
    "45": "豊橋",
    "46": "富山",
    "47": "松阪",
    "48": "四日市",
    "51": "福井",
    "53": "奈良",
    "54": "向日町",
    "55": "和歌山",
    "56": "岸和田",
    "61": "玉野",
    "62": "広島",
    "63": "防府",
    "71": "高松",
    "73": "小松島",
    "74": "高知",
    "75": "松山",
    "81": "小倉",
    "83": "久留米",
    "84": "武雄",
    "85": "佐世保",
    "86": "別府",
    "87": "熊本"
}