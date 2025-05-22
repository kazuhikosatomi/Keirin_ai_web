import requests
import os

# 保存先パス
DEST_PATH = 'db/keirin_ai.duckdb'
os.makedirs(os.path.dirname(DEST_PATH), exist_ok=True)

# Google Drive 共有リンクからの直接ダウンロードURL（ファイルIDを差し替え）
FILE_ID = '1j7jA0P4CP3J0-WGGCgVFNzvG7tCsiVDw'
URL = f'https://drive.google.com/uc?export=download&id={FILE_ID}'

print("📥 Downloading latest .duckdb from Google Drive...")

try:
    response = requests.get(URL)
    response.raise_for_status()
    with open(DEST_PATH, 'wb') as f:
        f.write(response.content)
    print(f"✅ Downloaded and saved to {DEST_PATH}")
except Exception as e:
    print(f"❌ Failed to download .duckdb: {e}")