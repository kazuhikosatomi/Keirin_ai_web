import requests
import os

def send_line_notify(message: str):
    line_token = os.environ.get("LINE_TOKEN")
    if not line_token:
        raise ValueError("LINE_TOKEN is not set in environment variables.")

    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {line_token}"
    }
    payload = {
        "message": message
    }
    response = requests.post(url, headers=headers, data=payload)
    response.raise_for_status()