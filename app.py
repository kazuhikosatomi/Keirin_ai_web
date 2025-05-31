from flask import Flask, render_template, request, jsonify
import duckdb

app = Flask(__name__)

# ✅ Google Drive 上の本番DBパス
con = duckdb.connect("/Users/satomi/Library/CloudStorage/GoogleDrive-itokeirinbu@gmail.com/マイドライブ/keirin_data.duckdb", read_only=True)

@app.route("/")
def index():
    dates = con.execute("SELECT DISTINCT date FROM \"entry\" ORDER BY date").fetchall()
    return render_template("index.html", dates=[d[0] for d in dates])

@app.route("/venue")
def venue():
    selected_date = request.args.get("date")
    venues = con.execute(
        f"SELECT DISTINCT venue_id FROM \"entry\" WHERE date = '{selected_date}' ORDER BY venue_id"
    ).fetchall()
    return {"venues": [v[0] for v in venues]}

@app.route("/race")
def race():
    selected_date = request.args.get("date")
    venue = request.args.get("venue")
    races = con.execute(f"""
        SELECT DISTINCT race_no FROM \"entry\"
        WHERE date = '{selected_date}' AND venue_id = '{venue}' ORDER BY race_no
    """).fetchall()
    return {"races": [r[0] for r in races]}

@app.route("/entry")
def entry():
    selected_date = request.args.get("date")
    venue = request.args.get("venue")
    race = request.args.get("race")

    print("🔍 selected_date:", selected_date)
    print("🔍 venue:", venue)
    print("🔍 race:", race)

    try:
        query = f"""
        SELECT *, grade AS class FROM \"entry\"
        WHERE date = '{selected_date}' AND venue_id = '{venue}' AND race_no = '{race}'
        """
        df = con.execute(query).fetchdf()
        df = df.fillna("")
        entries = df.to_dict(orient="records")
        return jsonify({"entries": entries})
    except Exception as e:
        print("🔥 例外発生:", e)
        return jsonify({"entries": []})

if __name__ == "__main__":
    app.run(debug=True)