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
subprocess.run(["python", "scripts/9th/9th_step6_evaluate_prediction.py", "--date", prev_date])
subprocess.run(["python", "scripts/9th/9th_step7_feedback_data.py", "--date", prev_date])

# 🟦 当日分（entryのみ）で予測処理
subprocess.run(["python", "scripts/9th/9th_step1_racer_stats.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step2_train_data.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step3_train_model.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step4_make_entry.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step5a_predict_racer.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step5b_aggregate_to_race.py", "--date", base_date])
subprocess.run(["python", "scripts/9th/9th_step5c_rank_race_arare.py", "--date", base_date])

# 📤 最終日だけ出力処理
subprocess.run(["python", "scripts/9th/9th_step8_generate_final_prediction.py", "--date", base_date])
