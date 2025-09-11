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
    subprocess.run(["python", "scripts/9th/9th_step6_evaluate_prediction.py", "--date", prev_date])
    subprocess.run(["python", "scripts/9th/9th_step7_feedback_data.py", "--date", prev_date])

    # 当日処理（予測）
    subprocess.run(["python", "scripts/9th/9th_step1_racer_stats.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step2_train_data.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step3_train_model.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step4_make_entry.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step5a_predict_racer.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step5b_aggregate_to_race.py", "--date", base_date])
    subprocess.run(["python", "scripts/9th/9th_step5c_rank_race_arare.py", "--date", base_date])

    subprocess.run(["python", "scripts/9th/9th_step8_generate_final_prediction.py", "--date", base_date])

    # 最終日のみ出力処理
    #if date == end_date:
        #subprocess.run(["python", "scripts/9th/9th_step8_generate_final_prediction.py", "--date", base_date])


print("\n全ての処理が終了しました")