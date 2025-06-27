import re
import csv
import pandas as pd
from entry_parser import fetch_entry_data
from datetime import datetime
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def main():
    import sys
    args = sys.argv[1:]

    if len(args) == 3:
        date_str_arg, venue_id_arg, race_num_arg = args
        mode = "single"
    elif len(args) == 2:
        date_str_arg, venue_id_arg = args
        mode = "venue_all"
    elif len(args) == 1:
        date_str_arg = args[0]
        mode = "all_from_calendar"
    else:
        print("Usage: python scrape_entry.py <date> [venue_id] [race_num]")   
        return

    date_str = date_str_arg if "-" in date_str_arg else f"{date_str_arg[:4]}-{date_str_arg[4:6]}-{date_str_arg[6:]}"
    all_entries = []

    if mode == "single":
        venues = [(venue_id_arg, [int(race_num_arg)])]
    elif mode == "venue_all":
        venues = [(venue_id_arg, list(range(1, 13)))]
    elif mode == "all_from_calendar":
        # Normalize date string to YYYYMMDD format for calendar lookup
        date_str_arg = date_str_arg.replace("-", "")
        calendar_path = os.path.join(BASE_DIR, "data/calendar/calendar_all.csv")
        calendar_df = pd.read_csv(calendar_path, dtype=str)
        calendar_df.columns = calendar_df.columns.str.strip()
        calendar_df = calendar_df[calendar_df["date"] == date_str_arg]
        venues = [(row["venue_id"], list(range(1, 13))) for _, row in calendar_df.iterrows()]

    for venue_id, race_nums in venues:
        print(f"📅 {date_str} | 🏟️ venue_id: {venue_id}")
        for race_num in race_nums:
            url = f"https://www.chariloto.com/keirin/athletes/{date_str}/{venue_id}/{race_num}"
            result = fetch_entry_data(url)
            print(f"🔍 result for {url} → {result}")
            entries = result.get("entries", [])
            if entries:
                print(f"  R{race_num}: {len(entries)}人", end=" ", flush=True)
            if "error" in result:
                continue
            if not entries:
                continue
            for entry in entries:
                entry["race_num"] = race_num
                entry["date"] = date_str
                entry["place_code"] = venue_id
            all_entries.extend(entries)
        print()

    # Load player master
    master_path = os.path.join(BASE_DIR, "data/master/player_master.csv")
    player_master_df = pd.read_csv(master_path, dtype=str).fillna("")

    # Strip all whitespace (full/half) and take first 5 characters of name_kanji
    def normalize_name(name):
        return re.sub(r'\s+', '', name)[:5]

    def strip_whitespace(val):
        return re.sub(r'\s+', '', val) if isinstance(val, str) else val

    name_to_racer_id = {
        normalize_name(row["name_kanji"]): row["racer_id"]
        for _, row in player_master_df.iterrows()
    }

    for entry in all_entries:
        norm_name = normalize_name(entry.get("name", ""))
        entry["racer_id"] = name_to_racer_id.get(norm_name, "")

    if not all_entries:
        print("⚠️ 有効な出走表データが1件も取得できませんでした")
        return

    year_folder = f"data/entries/{date_str_arg[:4]}"
    os.makedirs(year_folder, exist_ok=True)
    # Construct filename_suffix based on mode
    if mode == "single":
        filename_suffix = f"{date_str}-{venue_id_arg}-{race_num_arg}"
    elif mode == "venue_all":
        filename_suffix = f"{date_str}-{venue_id_arg}"
    elif mode == "all_from_calendar":
        filename_suffix = f"{date_str}"
    filename = os.path.join(year_folder, f"entry_{filename_suffix}.csv")
    with open(filename, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(all_entries[0].keys())
        if "racer_id" in fieldnames and "name" in fieldnames:
            fieldnames.remove("racer_id")
            name_index = fieldnames.index("name")
            fieldnames.insert(name_index + 1, "racer_id")
        rename_map = {
            "place_code": "venue_id",
            "race_num": "race_no",
            "frame_number": "frame_no",
            "name": "name_kanji",
            "leg_type": "style",
            "car_number": "car_no"
        }

        if "racer_id" not in fieldnames:
            try:
                name_index = fieldnames.index("name")
                fieldnames.insert(name_index + 1, "racer_id")
            except ValueError:
                fieldnames.append("racer_id")

        renamed_fieldnames = [rename_map.get(fn, fn) for fn in fieldnames]

        writer = csv.DictWriter(f, fieldnames=renamed_fieldnames)
        writer.writeheader()
        for row in all_entries:
            for key in ["recent_place1", "recent_place2", "recent_place3"]:
                if key in row:
                    row[key] = strip_whitespace(row[key])
                    if row[key] == "平":
                        row[key] = "いわき平"
                    elif row[key] == "京都":
                        row[key] = "向日町"
            renamed_row = {rename_map.get(k, k): v for k, v in row.items()}
            writer.writerow(renamed_row)

    print(f"📊 総レース数: {len(set([e['race_num'] for e in all_entries]))} | 総選手数: {len(all_entries)}")
    print(f"✅ 出力完了: {filename}")

if __name__ == "__main__":
    main()