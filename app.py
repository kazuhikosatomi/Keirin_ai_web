from flask import Flask, request, render_template, jsonify, make_response
from utils.entry_parser import fetch_entry_data  # 修正ポイント①
from utils.araredo_calc import calc_araredo      # 修正ポイント②
import duckdb
import os
import requests
import gdown
import pandas as pd
import datetime

GOOGLE_FILE_ID = "1LfWUJUw2BV0mqVrFx3qhfox44RQJk3J9"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "db", "keirin_ai.duckdb")

# DuckDBが存在しない場合はGoogle Driveからダウンロード
if not os.path.exists(OUTPUT_PATH):
    print("⬇️ Downloading .duckdb file from Google Drive...")
    url = f"https://drive.google.com/uc?id={GOOGLE_FILE_ID}"
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    gdown.download(url, OUTPUT_PATH, quiet=False)

app = Flask(__name__)

# DuckDBのDBファイルへのパス（適宜調整）
DB_PATH = OUTPUT_PATH
con = duckdb.connect(DB_PATH)


# venue_id を含んだ最新のカレンダーCSVを読み込み
calendar_df = pd.read_csv(
    "https://raw.githubusercontent.com/kazuhikosatomi/Keirin_ai_web/main/data/calendar/keirin_calendar_with_venue_id.csv",
    dtype={'venue_id': str}
)


# 日付から開催場一覧を取得
def get_venues_for_date(date_str):
    return calendar_df[calendar_df['date'] == date_str][['venue_id', 'venue_name']].drop_duplicates().to_dict('records')

# カレンダーデータをJSONで返すAPI
@app.route('/calendar_data')
def calendar_data():
    response = make_response(calendar_df.to_json(force_ascii=False, orient='records'))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

# 🔸出走表取得UI（index.html）
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    today = datetime.date.today().strftime("%Y-%m-%d")

    if request.method == 'POST':
        date = request.form['date']
        venue_id = request.form['venue_id']
        race = request.form['race']
        url = f"http://chariloto.com/keirin/athletes/{date}/{venue_id}/{race}"
        try:
            print("✅ fetch_entry_data() 開始")
            print("🔗 URL:", url)
            data = fetch_entry_data(url)
            print("📦 登録データ件数:", len(data.get("entries", [])))
            if "error" in data:
                result = {"error": data["error"]}
            else:
                result = {
                    "entries": data["entries"],
                    "meta": data["meta"]
                }
        except Exception as e:
            import traceback
            error_message = traceback.format_exc()
            print("❌ エラー:", e)
            print(error_message)
            result = {'error': error_message}
        venues = get_venues_for_date(date)
        return render_template('index.html', result=result, venues=venues, today=date, selected_venue=venue_id, selected_race=race)

    venues = get_venues_for_date(today)
    return render_template('index.html', result=result, venues=venues, today=today)

# 🔸荒れ度予測API（GETで使用）
@app.route('/araredo_predict', methods=['GET'])
def araredo_predict():
    date = request.args.get('date').replace('-', '')
    venue_id = request.args.get('venue_id')
    race_no = request.args.get('race')

    if not all([date, venue_id, race_no]):
        return jsonify({"error": "Missing parameters"}), 400

    query = f"""
    WITH odds_filtered AS (
      SELECT
        date,
        venue_id,
        race_no,
        odds1
      FROM odds
      WHERE bet_code = 3
        AND date = {date}
        AND venue_id = {venue_id}
        AND race_no = {race_no}
    ),
    agg AS (
      SELECT
        MIN(odds1) AS lowest_odds,
        MEDIAN(odds1) AS median_odds,
        SUM(odds1) AS total_sum
      FROM odds_filtered
    ),
    top3 AS (
      SELECT SUM(odds1) AS top3_sum
      FROM (
        SELECT odds1
        FROM odds_filtered
        ORDER BY odds1 ASC
        LIMIT 3
      )
    )
    SELECT
      agg.lowest_odds,
      agg.median_odds,
      ROUND(top3.top3_sum / agg.total_sum, 5) AS top3_ratio
    FROM agg, top3;
    """

    result = con.execute(query).fetchone()

    if not result or result[0] is None:
        return jsonify({"error": "No odds data found for this race"}), 404

    lowest_odds, median_odds, top3_ratio = result
    score = calc_araredo(lowest_odds, median_odds, top3_ratio)

    return jsonify({
        "date": date,
        "venue_id": venue_id,
        "race_no": race_no,
        "lowest_odds": lowest_odds,
        "median_odds": median_odds,
        "top3_ratio": top3_ratio,
        "araredo_score": score
    })

# 🔸Flaskアプリ起動

# 🔸レースごと荒れ度リスト表示
@app.route('/list_predict', methods=['GET', 'POST'])
def list_predict():
    result = []
    if request.method == 'POST':
        date = request.form['date']
        venue_id = request.form['venue_id']
        for race in range(1, 13):
            try:
                url = f"{request.url_root}araredo_predict?date={date}&venue_id={venue_id}&race={race}"
                r = requests.get(url)
                if r.status_code == 200:
                    score = r.json().get("araredo_score", "N/A")
                    entry_url = f"https://example.com/{date}/{venue_id}/{race}"  # URL should be constructed appropriately
                    data = fetch_entry_data(entry_url)
                    main_riders = [str(entry['car_number']) for entry in data.get('entries', []) if entry.get('line_pos') == 1]
                    result.append((race, score, "-".join(main_riders)))
                else:
                    break
            except Exception:
                break
    return render_template("list.html", result=result)

# ① Flaskルーティング定義をここに書く
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_data = request.get_data()
        print("📥 Webhook (raw):", raw_data, flush=True)

        import json
        body = json.loads(raw_data.decode("utf-8"))
        print("📥 Webhook受信(JSON):", body, flush=True)

        events = body.get("events", [])
        print(f"📊 イベント数: {len(events)}", flush=True)

        for event in events:
            print("🔸イベント内容:", event, flush=True)
            if event.get("type") == "message":
                user_id = event["source"].get("userId", "(unknown)")
                print(f"👤 userId: {user_id}", flush=True)
    except Exception as e:
        print("⚠️ Webhook処理エラー:", e, flush=True)

    return "OK", 200

# ② その下に Flask の起動条件を書く（Render用）
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5050))  # Render用
    app.run(host='0.0.0.0', port=port)