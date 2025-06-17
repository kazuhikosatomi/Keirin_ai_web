from flask import Flask, request
import json

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_data(as_text=True)
    try:
        events = json.loads(body).get("events", [])
        for event in events:
            user_id = event.get("source", {}).get("userId")
            if user_id:
                with open("logged_user_ids.txt", "a") as f:
                    f.write(f"{user_id}\n")
                print(f"✅ userId: {user_id}")
    except Exception as e:
        print("❌ Error:", e)
    return "OK"

@app.route("/list_user_ids", methods=["GET"])
def list_ids():
    try:
        with open("logged_user_ids.txt", "r") as f:
            return f"<pre>{f.read()}</pre>"
    except FileNotFoundError:
        return "<pre>まだ取得された userId はありません。</pre>"