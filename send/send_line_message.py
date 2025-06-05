import os
import requests
import json
import datetime
import pandas as pd

def should_send_today():
    return datetime.datetime.now().weekday() != 2  # 水曜スキップ

ACCESS_TOKEN = os.environ.get("LINE_TOKEN")
USER_IDS = os.environ.get("LINE_USER_IDS", "").split(";")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

today_str = datetime.datetime.now().strftime("%Y-%m-%d")
predict_file = f"output/predict/train.predicted_rank_{today_str}.csv"

if os.path.exists(predict_file):
    df = pd.read_csv(predict_file)
    top3 = df.sort_values("predicted_rank").groupby(["date", "venue_id", "race_no"]).head(1)
    top3 = top3.sort_values("predicted_rank").head(3)

    lines = []
    for row in top3.itertuples():
        lines.append(f"・{row.venue_name} {int(row.race_no)}R：{int(row.car_no)} {row.name_kanji}")
    detail_url = f"https://keirin-ai.example.com/{today_str}"
    message_text = f"【{today_str} AI予測】\n🏆 本命予想（1着）\n\n" + "\n".join(lines) + f"\n\n詳細👇\n{detail_url}"
else:
    message_text = f"{today_str} の予測結果ファイルが見つかりませんでした。"

message = {
    "type": "text",
    "text": message_text
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