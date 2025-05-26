import os
import pandas as pd

# bet_master.csv の読み込み
script_dir = os.path.dirname(os.path.abspath(__file__))
master_path = os.path.join(script_dir, "../../data/master/bet_master.csv")
bet_master = pd.read_csv(master_path)
type_to_code = dict(zip(bet_master["bet_type"], bet_master["bet_code"]))

# 対象のルートディレクトリ
root_dir = os.path.expanduser("~/Documents/keirin/odds")

for subdir in os.listdir(root_dir):
    if not subdir.endswith("fix"):
        continue

    input_folder = os.path.join(root_dir, subdir)
    output_folder = os.path.join(root_dir, subdir.replace("fix", ""))
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if not file.startswith("chariloto_odds_") or not file.endswith(".csv"):
            continue

        input_path = os.path.join(input_folder, file)
        try:
            df = pd.read_csv(input_path)

            # 日付フォーマット
            df["date"] = pd.to_datetime(df["日付"].astype(str), errors="coerce").dt.strftime("%Y-%m-%d")

            # レース番号
            df["race_no"] = df["レース"].str.extract(r"(\d+)").astype("Int64")

            # 組番分解
            car_split = df["組番"].astype(str).str.split("-", expand=True)
            df["car_1"] = pd.to_numeric(car_split[0], errors="coerce").astype("Int64")
            df["car_2"] = pd.to_numeric(car_split[1], errors="coerce").astype("Int64")
            df["car_3"] = pd.to_numeric(car_split[2], errors="coerce").astype("Int64") if car_split.shape[1] > 2 else pd.NA

            # オッズ
            odds_split = df["オッズ"].astype(str).str.split("〜", expand=True)
            df["odds_1"] = pd.to_numeric(odds_split[0], errors="coerce")
            df["odds_2"] = pd.to_numeric(odds_split[1], errors="coerce") if 1 in odds_split.columns else pd.NA

            # bet_code 補完
            df["bet_code"] = df["賭式"].map(type_to_code).astype("Int64")

            # venue_id
            df["venue_id"] = pd.to_numeric(df["場コード"], errors="coerce").astype("Int64")

            # 出力用データ構造
            df_final = df[[
                "date", "venue_id", "race_no", "bet_code",
                "car_1", "car_2", "car_3", "odds_1", "odds_2"
            ]]

            date_str = df_final["date"].dropna().iloc[0]
            output_filename = f"odds_{date_str}.csv"
            output_path = os.path.join(output_folder, output_filename)
            df_final.to_csv(output_path, index=False, encoding="utf-8-sig")

            print(f"✅ 保存完了: {output_filename}")

        except Exception as e:
            print(f"❌ エラー: {file} - {e}")