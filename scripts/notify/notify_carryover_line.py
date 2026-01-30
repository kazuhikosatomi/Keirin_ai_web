import pandas as pd
import os
from datetime import datetime
from utils.line_notify import send_line_notify  # すでにある送信関数を使う

# 実行日
today = datetime.now().strftime("%Y-%m-%d")
year = datetime.now().strftime("%Y")
month = datetime.now().strftime("%m")

# ファイルパス
file_path = f"data/carryover/{year}/{month}/carryover_info_{today}.csv"

if not os.path.exists(file_path):
    print(f"❌ ファイルが存在しません: {file_path}")
    exit()

df = pd.read_csv(file_path)

# 通知対象の抽出条件
target_df = df[
    (df["くじ"].str.contains("チャリロト5")) &
    (df["キャリーオーバー"].str.contains("円")) &
    (df["キャリーオーバー"].str.replace(",", "").str.replace("円", "").astype(int) >= 1_000_000) &
    (df["次回発売予定"].str.contains("発売中"))
]

if target_df.empty:
    print("📭 通知対象なし（キャリーオーバー100万円以上で発売中のチャリロト5）")
else:
    message = f"📣 キャリーオーバー情報（{today}）\n"
    for _, row in target_df.iterrows():
        message += f"🏟 {row['競輪場名']}｜{row['くじ']}：{row['キャリーオーバー']}（{row['次回発売予定']}）\n"
    send_line_notify(message)
    print("✅ LINE通知を送信しました")