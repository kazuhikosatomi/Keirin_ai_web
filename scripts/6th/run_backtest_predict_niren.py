import argparse
from datetime import datetime, timedelta
import subprocess

def run_steps_for_date(target_date: str, end_date: str):
    print(f"\n📅 {target_date} の処理を開始します")

    steps = [
        "6th_step1_generate_racer_stats.py",
        "6th_step2_generate_train_racer_level_niren.py",
        "6th_step3_train_model.py",
        "6th_step4_generate_entry_like.py",
        "6th_step5_predict_rank.py",
        "6th_step6_evaluate_prediction_niren.py",
        "6th_step7_feedback_train_data_niren.py",
    ]

    for i, step in enumerate(steps, start=1):
        print(f"\n🚀 Step{i}: 実行中: {step}")
        try:
            subprocess.run(
                ["python", f"scripts/6th/{step}", "--date", target_date],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"❌ エラーが発生しました: {step}")
            break

        # After Step 5, check if target_date == end_date to skip Steps 6 and 7
        if step == "6th_step5_predict_rank.py" and target_date == end_date:
            print("✅ 最終日のため Step6/7 をスキップします")
            break

    if target_date == end_date:
        print(f"\n🚀 Step8: 実行中: 6th_step8_generate_final_prediction_niren.py")
        try:
            subprocess.run(
                ["python", "scripts/6th/6th_step8_generate_final_prediction_niren.py", "--date", target_date],
                check=True
            )
        except subprocess.CalledProcessError:
            print("❌ エラーが発生しました: 6th_step8_generate_final_prediction_niren.py")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="終了日 (YYYY-MM-DD)")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    current_date = start_date
    while current_date <= end_date:
        run_steps_for_date(str(current_date), str(end_date))
        current_date += timedelta(days=1)

if __name__ == "__main__":
    main()