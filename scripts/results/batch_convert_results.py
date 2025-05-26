
import os
import pandas as pd

# ファイル読み込みパス
script_dir = os.path.dirname(os.path.abspath(__file__))
player_path = os.path.join(script_dir, "../../data/master/player_master.csv")
venue_path = os.path.join(script_dir, "../../data/master/venue_master.csv")

# player_master 読み込みと整形
player_df = pd.read_csv(player_path)
def normalize_name(name):
    return str(name).replace(" ", "").replace("　", "").strip()
def short_key(name):
    return normalize_name(name)[:5]
player_df["short_name"] = player_df["name_kanji"].apply(short_key)

# タクティクス略記
tactics_map = {"逃げ": "逃", "マーク": "マ", "差し": "差", "捲くり": "捲"}

# 変換対象ルート
root_dir = os.path.expanduser("~/Documents/keirin/results")

for subdir in os.listdir(root_dir):
    if not subdir.endswith("fix"):
        continue

    input_folder = os.path.join(root_dir, subdir)
    output_folder = os.path.join(root_dir, subdir.replace("fix", ""))
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if not file.startswith("chariloto_results_") or not file.endswith(".csv"):
            continue

        input_path = os.path.join(input_folder, file)
        try:
            df = pd.read_csv(input_path)

            # 名前キー追加と結合
            df["short_name"] = df["選手名"].apply(short_key)
            df = pd.merge(df, player_df[["racer_id", "short_name"]], on="short_name", how="left")
            df["name_kanji"] = df["選手名"]

            # カラム英語変換
            df = df.rename(columns={
                "日付": "date",
                "レース場": "venue_name",
                "場コード": "venue_id",
                "レース": "race_no",
                "順位": "rank",
                "車番": "car_no",
                "年齢": "age",
                "府県": "prefecture",
                "級班": "grade",
                "着差": "margin",
                "上り": "last_time",
                "決まり手": "finish_tactics",
                "S": "s_mark",
                "B": "b_mark"
            })

            df["race_no"] = df["race_no"].str.replace("R", "").astype("Int64")
            df["finish_tactics"] = df["finish_tactics"].map(tactics_map).fillna(df["finish_tactics"])

            columns_order = [
                "date", "venue_name", "venue_id", "race_no", "rank", "car_no",
                "name_kanji", "racer_id", "age", "prefecture", "grade", "margin", "last_time",
                "finish_tactics", "s_mark", "b_mark", "line_id", "line_pos"
            ]
            df = df[columns_order]

            date_str = df["date"].dropna().iloc[0]
            output_filename = f"results_{date_str}.csv"
            output_path = os.path.join(output_folder, output_filename)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"✅ 保存完了: {output_filename}")

        except Exception as e:
            print(f"❌ エラー: {file} - {e}")
