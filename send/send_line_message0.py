import os
import requests
import json
import datetime
import pandas as pd
import pytz

def should_send_today():
    return datetime.datetime.now().weekday() != 2  # 水曜スキップ（今は仮）

ACCESS_TOKEN = os.environ.get("LINE_TOKEN")
USER_IDS = os.environ.get("LINE_USER_IDS", "").split(";")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

import pytz
jst = datetime.datetime.now(pytz.timezone("Asia/Tokyo"))
today_str = jst.strftime("%Y-%m-%d")

predict_file = f"output/predict/train.predicted_rank_{today_str}.csv"


if os.path.exists(predict_file):
    df = pd.read_csv(predict_file)

    # 1位・2位を race_no 単位で抽出
    top2_per_race = df[df["predicted_rank"].isin([1, 2])]
    # 2人揃っているレースだけに絞る
    valid_races = top2_per_race.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(lambda x: len(x) == 2)

    # 各レースでスコアを合計
    grouped = valid_races.groupby(["date", "venue_id", "venue_name", "race_no"])
    race_scores = grouped["predicted_score"].sum().reset_index(name="total_score")

    # 上位3レース抽出
    top3_races = race_scores.sort_values("total_score", ascending=False).head(3)

    lines = []
    for _, race in top3_races.iterrows():
        racers = valid_races[
            (valid_races["date"] == race["date"]) &
            (valid_races["venue_id"] == race["venue_id"]) &
            (valid_races["race_no"] == race["race_no"])
        ].sort_values("predicted_rank")

        car_nos = "-".join(str(int(c)) for c in racers["car_no"])
        names = "-".join(racers["name_kanji"])
        lines.append(f"・{race['venue_name']} {int(race['race_no'])}R：{car_nos}（{names}） [Score: {race['total_score']:.2f}]")

    detail_url = f"https://keirin-ai.example.com/{today_str}"
    message_text = f"【{today_str} AI予測】\n🎯 本日の注目2車単予想\n\n" + "\n".join(lines) + f"\n\n🔗 詳細：{detail_url}"
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
