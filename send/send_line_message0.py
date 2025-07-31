import os
import argparse
import requests
import json
import datetime
import pandas as pd
import pytz
import re

# argparseによるコマンドライン引数処理
parser = argparse.ArgumentParser()
parser.add_argument('--dryrun', action='store_true', help='LINEには送らず、printだけする')
args = parser.parse_args()

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

predict_file = f"docs/predict/csv/3rd/final_prediction_niren_{today_str}.csv"


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
    lines.append("🎯 本日の注目予想（２車単）")
    lines.append("")
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
        # 表示を car_no + name に変更
        racer1_display = f"{car_nos[0]} {name1}"
        racer2_display = f"{car_nos[1]} {name2}"
        # 修正後のメッセージ行追加
        lines.append(f"{race['venue_name']} {int(race['race_no'])}R：{car_nos[0]}-{car_nos[1]}")
        lines.append(f"{racer1_display}-{racer2_display}")
        lines.append(f"Score: {race['total_score']:.2f}")
        lines.append("")  # 空行を追加して見やすくする

    predict_file_trio = f"output/predict/4th/final_prediction_trio_{today_str}.csv"
    if os.path.exists(predict_file_trio):
        df_trio = pd.read_csv(predict_file_trio)
        if "grade" in df_trio.columns:
            df_trio["grade"] = df_trio["grade"].astype(str).str.translate(str.maketrans({
                'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E', 'Ｆ': 'F', 'Ｇ': 'G',
                'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J', 'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N',
                'Ｏ': 'O', 'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T', 'Ｕ': 'U',
                'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z',
                '１': '1', '２': '2', '３': '3', '４': '4', '５': '5', '６': '6',
                '７': '7', '８': '8', '９': '9', '０': '0',
            }))
            top3_per_race = df_trio[df_trio["predicted_rank"].isin([1, 2, 3])]
            valid_races_trio = top3_per_race.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(lambda x: len(x) == 3)
            def exclude_l1_a3_trio(gr):
                grades = set(gr["grade"].tolist())
                return not ("L1" in grades or "A3" in grades)
            df_trio = valid_races_trio.groupby(["date", "venue_id", "venue_name", "race_no"]).filter(exclude_l1_a3_trio)
        grouped_trio = df_trio.groupby(["date", "venue_id", "venue_name", "race_no"])
        score_col_trio = "predicted_score"
        if score_col_trio not in df_trio.columns:
            score_candidates_trio = [col for col in df_trio.columns if "score" in col]
            if score_candidates_trio:
                score_col_trio = score_candidates_trio[0]
        race_scores_trio = grouped_trio[score_col_trio].sum().reset_index(name="total_score")
        top_races_trio = race_scores_trio.sort_values("total_score", ascending=True).head(3)

        lines.append("🎯 本日の注目予想（３連複）")
        lines.append("")

        for _, race in top_races_trio.iterrows():
            racers = df_trio[
                (df_trio["date"] == race["date"]) &
                (df_trio["venue_id"] == race["venue_id"]) &
                (df_trio["race_no"] == race["race_no"])
            ].sort_values("predicted_rank")
            car_nos = [int(c) for c in racers["car_no"]]
            # 修正：三連複の表示をハイフン区切りに変更し、車番をソート
            car_nos_sorted = sorted(car_nos)
            car_nos_str = "-".join(str(c) for c in car_nos_sorted)
            names = list(racers["name_kanji"])
            # 各選手の表示を car_no + name に変更し3段表示、新しい行で表示
            racer_displays = []
            # マッピング car_no -> name_clean
            car_no_to_name = {int(c): re.sub(r'\s+', ' ', n.strip()) for c, n in zip(racers["car_no"], names)}
            for c_no in car_nos_sorted:
                name_clean = car_no_to_name.get(c_no, "")
                racer_displays.append(f"{c_no} {name_clean}")

            lines.append(f"{race['venue_name']} {int(race['race_no'])}R（三連複）: {car_nos_str}")
            lines.extend(racer_displays)
            lines.append(f"Score: {race['total_score']:.2f}")
            lines.append("")
            # Trio prediction debug output
            print(f"✅ 三連複: {race['venue_name']} {int(race['race_no'])}R - {car_nos_str}")
            for rd in racer_displays:
                print(f"　{rd}")
            print("")

    if not lines:
        print("⚠️ 有効な2車単候補が見つかりませんでした。")
    else:
        print("✅ 通知メッセージを作成しました。")

    detail_url = "https://kazuhikosatomi.github.io/Keirin_ai_web/"
    message_text = f"【{today_str} AI予測】\n\n" + "\n".join(lines) + f"\n🔗 詳細：{detail_url}"
else:
    message_text = f"{today_str} の予測結果ファイルが見つかりませんでした。"
    print(message_text)

print("📨 送信メッセージ:")
print(message_text)

if args.dryrun:
    print("🚫 LINE送信はスキップされました (--dryrun 指定)")
    exit()

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