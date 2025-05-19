from flask import Flask, request, render_template, jsonify
from utils.entry_parser import fetch_entry_data  # 修正ポイント①
from utils.araredo_calc import calc_araredo      # 修正ポイント②
import duckdb
import requests

app = Flask(__name__)

# DuckDBのDBファイルへのパス（適宜調整）
con = duckdb.connect("/Users/satomi/Documents/keirin_ai/db/keirin_ai.duckdb")

# 🔸出走表取得UI（index.html）
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        url = request.form['url']
        try:
            data = fetch_entry_data(url)
            if "error" in data:
                result = {"error": data["error"]}
            else:
                result = {
                    "entries": data["entries"],
                    "meta": data["meta"]
                }
        except Exception as e:
            result = {'error': str(e)}
    return render_template('index.html', result=result)

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
                url = f"http://localhost:5050/araredo_predict?date={date}&venue_id={venue_id}&race={race}"
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=False)  # ← debug=False に変更