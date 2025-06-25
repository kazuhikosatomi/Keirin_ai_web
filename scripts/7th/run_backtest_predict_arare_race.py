import subprocess
from datetime import datetime, timedelta
import argparse
from pathlib import Path

# 引数解析
parser = argparse.ArgumentParser()
parser.add_argument("--start", type=str, required=True, help="バックテスト開始日 (YYYY-MM-DD)")
parser.add_argument("--end", type=str, required=True, help="バックテスト終了日 (YYYY-MM-DD)")
args = parser.parse_args()

start_date = datetime.strptime(args.start, "%Y-%m-%d")
end_date = datetime.strptime(args.end, "%Y-%m-%d")

date_list = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

for date in date_list:
    base_date = date.strftime("%Y-%m-%d")
    prev_date = (date - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\n==== 処理開始: {base_date} ====")

    # 前日処理（フィードバック）
    subprocess.run(["python", "scripts/7th/7th_step6_generate_label_arare.py", "--date", prev_date])
    subprocess.run(["python", "scripts/7th/7th_step7_answer_check.py", "--date", prev_date])

    # 当日処理（予測）
    subprocess.run(["python", "scripts/7th/7th_step1_generate_race_features.py", "--date", base_date])
    subprocess.run(["python", "scripts/7th/7th_step2_merge_labels_and_features.py", "--date", base_date])
    subprocess.run(["python", "scripts/7th/7th_step3_prepare_train_data.py", "--date", base_date])
    subprocess.run(["python", "scripts/7th/7th_step4_train_model.py", "--date", base_date])
    subprocess.run(["python", "scripts/7th/7th_step5_1_prepare_predict_features.py", "--date", base_date])
    subprocess.run(["python", "scripts/7th/7th_step5_2_predict_arare_race.py", "--date", base_date])

    # 最終日のみ出力処理
    if date == end_date:
        subprocess.run(["python", "scripts/7th/7th_step8_export_csv.py", "--date", base_date])
        subprocess.run(["python", "scripts/7th/7th_step9_export_pdf.py", "--date", base_date])

print("\n全ての処理が終了しました")