import os
import requests
import json
import datetime

def should_send_today():
    return datetime.datetime.now().weekday() != 2  # 水曜スキップ

ACCESS_TOKEN = os.environ.get("LINE_TOKEN")
USER_IDS = os.environ.get("LINE_USER_IDS", "").split(";")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

message = {
    "type": "text",
    "text": "✅ アタルくんからの通知が届いたよ！"
}

if should_send_today():
    for user_id in USER_IDS:
        if not user_id.strip():
            continue
        payload = {
            "to": user_id.strip(),
            "messages": [message]
        }
        res = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=payload
        )
        print(f"📤 To {user_id.strip()} => Status: {res.status_code}, Response: {res.text}")
else:
    print("⏸ 水曜日のため送信スキップ")