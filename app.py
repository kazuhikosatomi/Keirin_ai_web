# app.py（LINE Webhook 専用）

from flask import Flask, request
import json
from datetime import datetime

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_data(as_text=True)
    print("📨 Webhook受信:", body)
    try:
        events = json.loads(body).get("events", [])
        for event in events:
            if event.get("type") == "message":
                user_id = event.get("source", {}).get("userId")
                message = event.get("message", {}).get("text", "")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 保存（重複チェックや改行処理は必要に応じて）
                with open("line_user_ids.csv", "a") as f:
                    f.write(f"{user_id},{timestamp},{message}\n")

                print(f"✅ userId 取得: {user_id} | msg: {message}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return "OK"

from flask import send_file
import os

@app.route("/download_userids")
def download_userids():
    filepath = "line_user_ids.csv"
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return "CSVファイルが見つかりません", 404


# Renderでのポート認識に対応
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)