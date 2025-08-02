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
    subprocess.run(["python", "scripts/3rd/3rd_step7_feedback_train_data_niren.py", "--date", prev_date])
    
    # 前日処理（結果追記）
    subprocess.run(["python", "scripts/3rd/3rd_stepA_merge_prediction_with_results.py", "--date", prev_date])
    subprocess.run(["python", "scripts/3rd/3rd_stepB_generate_pdf_niren.py", "--date", prev_date])

    # 当日処理（予測）
    subprocess.run(["python", "scripts/3rd/3rd_step0_generate_race_features.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step1_generate_racer_stats.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step2_generate_train_racer_level_niren.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step3_train_model.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step4_generate_entry_like.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step5_predict_rank.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step6_evaluate_prediction_niren.py", "--date", base_date])
    subprocess.run(["python", "scripts/3rd/3rd_step8_generate_final_prediction_niren.py", "--date", base_date])
    
    # 最終日のみ出力処理
    if date == end_date:
        subprocess.run(["python", "scripts/3rd/3rd_step9_generate_pdf_niren.py", "--date", base_date])

print("\n全ての処理が終了しました")