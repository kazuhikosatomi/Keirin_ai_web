import argparse
from datetime import datetime
from datetime import timedelta
import subprocess

# 🔧 引数処理：--date がなければ今日の日付を使う
parser = argparse.ArgumentParser()
parser.add_argument("--date", type=str, help="基準日（YYYY-MM-DD）")
args = parser.parse_args()

base_date = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
prev_date = (datetime.strptime(base_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

print(f"📅 基準日: {base_date}")

# 🟥 前日分（結果が出ているデータ）で答え合わせとフィードバック
subprocess.run(["python", "scripts/7th/7th_step6_generate_label_arare.py", "--date", prev_date])
subprocess.run(["python", "scripts/7th/7th_step7_answer_check.py", "--date", prev_date])

# 🟦 当日分（entryのみ）で予測処理
subprocess.run(["python", "scripts/7th/7th_step1_generate_race_features.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step2_merge_labels_and_features.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step3_prepare_train_data.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step4_train_model.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step5_1_prepare_predict_features.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step5_2_predict_arare_race.py", "--date", base_date])

# 📤 最終日だけ出力処理
subprocess.run(["python", "scripts/7th/7th_step8_export_csv.py", "--date", base_date])
subprocess.run(["python", "scripts/7th/7th_step9_export_pdf.py", "--date", base_date])