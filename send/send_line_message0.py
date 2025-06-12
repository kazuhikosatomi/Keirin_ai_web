import os
import requests
import json
import datetime
import pandas as pd
import pytz
import re

def should_send_today():
    return True  # 毎日送信に変更

ACCESS_TOKEN = os.environ.get("LINE_TOKEN")
USER_IDS = os.environ.get("LINE_USER_IDS", "").split(";")

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

import pytz
jst = datetime.datetime.now(pytz.timezone("Asia/Tokyo"))
today_str = jst.strftime("%Y-%m-%d")

predict_file = f"output/predict/final_prediction_{today_str}.csv"


if os.path.exists(predict_file):
    df = pd.read_csv(predict_file)
    # 'grade'カラムでL1/A3を除外
    if "grade" in df.columns:
        # Normalize 'grade' column from full-width to half-width characters
        df["grade"] = df["grade"].astype(str).str.translate(str.maketrans({
            'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F', 'Ｇ': 'G',
            'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N',
            'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U',
            'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z',
            '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6',
            '７': '7', '８': '8', '９': '9', '０': '0',
        }))
        # Filter for top 2 predicted ranks first
        top2_per_race = df[df["predicted_rank"].isin([1, 2])]
        # Group by race and keep only those with 2 entries
        valid_races = top2_per_race.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(lambda x: len(x) == 2)
        # Then remove any race where one of the grades is L1 or A3
        def exclude_l1_a3(gr):
            grades = set(gr["grade"].tolist())
            return not ("L1" in grades or "A3" in grades)
        df = valid_races.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(exclude_l1_a3)
    else:
        print("⚠️ 'grade' カラムが存在しないため、フィルタリングをスキップします。")

    # 1位・2位を race_no 単位で抽出
    # top2_per_race = df[df["predicted_rank"].isin([1, 2])]  # No longer needed
    # 2人揃っているレースだけに絞る
    # valid_races = top2_per_race.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(lambda x: len(x) == 2)  # No longer needed

    # 各レースでスコアを合計
    grouped = df.groupby(["date", "venue_id", "venue_name", "race_no"])
    score_col = "predicted_score"
    if score_col not in df.columns:
        score_candidates = [col for col in df.columns if "score" in col]
        if score_candidates:
            score_col = score_candidates[0]  # 最初に見つかった候補を使用
    race_scores = grouped[score_col].sum().reset_index(name="total_score")

    # 上位3レース抽出
    top_races = race_scores.sort_values("total_score", ascending=True).head(3)

    lines = []
    for _, race in top_races.iterrows():
        racers = df[
            (df["date"] == race["date"]) &
            (df["venue_id"] == race["venue_id"]) &
            (df["race_no"] == race["race_no"])
        ].sort_values("predicted_rank")

        car_nos = [str(int(c)) for c in racers["car_no"]]
        names = list(racers["name_kanji"])
        # 正規化処理を追加
        name1 = re.sub(r'\s+', ' ', names[0].strip())
        name2 = re.sub(r'\s+', ' ', names[1].strip())
        # 修正後のメッセージ行追加
        lines.append(f"{race['venue_name']} {int(race['race_no'])}R：{car_nos[0]}-{car_nos[1]}")
        lines.append(f"{name1}-{name2}")
        lines.append(f"Score: {race['total_score']:.2f}")
        lines.append("")  # 空行を追加して見やすくする

    if not lines:
        print("⚠️ 有効な2車単候補が見つかりませんでした。")
    else:
        print("✅ 通知メッセージを作成しました。")

    detail_url = f"https://keirin-ai.example.com/{today_str}"
    message_text = f"【{today_str} AI予測】\n🎯 本日の注目2車単予想\n\n" + "\n".join(lines) + f"\n🔗 詳細：{detail_url}"
else:
    message_text = f"{today_str} の予測結果ファイルが見つかりませんでした。"
    print(message_text)

message = {
    "type": "text",
    "text": message_text
}

if should_send_today():
    print("📦 メッセージ内容:\n" + message_text)
    for user_id in USER_IDS:
        if not user_id.strip():
            print("⚠️ USER_IDが設定されていません。")
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
