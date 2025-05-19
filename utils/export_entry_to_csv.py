import sys
import csv
from entry_parser import fetch_entry_data

def main():
    if len(sys.argv) != 4:
        print("使用方法: python3 export_entry_to_csv.py YYYY-MM-DD PLACE_CODE RACE_NUM")
        sys.exit(1)

    date_str = sys.argv[1]
    place_code = sys.argv[2]
    race_num = sys.argv[3]

    url = f"https://www.chariloto.com/keirin/athletes/{date_str}/{place_code}/{race_num}"
    print(f"🔍 URL: {url}")

    result = fetch_entry_data(url)
    if "error" in result:
        print(f"❌ エラー: {result['error']}")
        sys.exit(1)

    entries = result["entries"]
    if not entries:
        print("⚠️ 選手情報がありません")
        sys.exit(1)

    filename = f"entry_export_{date_str}_{place_code}_{race_num}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=entries[0].keys())
        writer.writeheader()
        writer.writerows(entries)

    print(f"✅ CSV出力完了: {filename}")

if __name__ == "__main__":
    main()