import requests
import json

# チャネルアクセストークン
ACCESS_TOKEN = 'BwGrH6y8tZX64RYfQq1RMiBDrtx8AkyzWfw9433F5H/UxA2InnZ+v+ORa1hxa8jTqNL9tbKKYmgEsJZ8b8bF8kGqhNwp1vKd3/kBAzxn0sN/EuM0Mls20zUtQ+CBfFOlUfXkHbUuN64wsUTa9e7/UAdB04t89/1O/w1cDnyilFU='

# 👇 新しい userId を使用！
USER_ID = 'Ue9ad8031a3ed1611fa0c7c79a84ac45c'

# メッセージデータ
payload = {
    "to": USER_ID,
    "messages": [
        {
            "type": "text",
            "text": "✅ アタルくんからの通知が届いたよ！"
        }
    ]
}

# ヘッダー情報
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# APIに送信
res = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers=headers,
    json=payload  # ← ここを修正：json= にする
)

# 結果表示
print("✅ ステータスコード:", res.status_code)
print("📬 レスポンス:", res.text)