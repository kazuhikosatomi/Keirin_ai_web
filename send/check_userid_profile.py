import requests

ACCESS_TOKEN = 'BwGrH6y8tZX64RYfQq1RMiBDrtx8AkyzWfw9433F5H/UxA2InnZ+v+ORa1hxa8jTqNL9tbKKYmgEsJZ8b8bF8kGqhNwp1vKd3/kBAzxn0sN/EuM0Mls20zUtQ+CBfFOlUfXkHbUuN64wsUTa9e7/UAdB04t89/1O/w1cDnyilFU='
USER_ID = 'Ue9ad8031a3a16d11fa01c77a98a4c45c'

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

res = requests.get(
    f"https://api.line.me/v2/bot/profile/{USER_ID}",
    headers=headers
)

print("📡 ステータス:", res.status_code)
print("🧾 レスポンス:", res.text)