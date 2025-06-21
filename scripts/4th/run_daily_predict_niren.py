import argparse
from datetime import datetime, timedelta
import subprocess

def run_daily_prediction(today: str, yesterday: str):
    print(f"\n📅 {today} の予測処理を開始します")

    # Step 6 and 7 for yesterday
    for i, step in enumerate([
        "4th_step6_evaluate_prediction_niren.py",
        "4th_step7_feedback_train_data_niren.py"
    ], start=6):
        print(f"\n🔁 Step{i}: 実行中（昨日のデータ）: {step}")
        try:
            subprocess.run(
                ["python", f"scripts/4th/{step}", "--date", yesterday],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"❌ エラーが発生しました: {step}")
            return

    # Step 1 to 5 for today
    for i, step in enumerate([
        "4th_step1_generate_racer_stats.py",
        "4th_step2_generate_train_racer_level_niren.py",
        "4th_step3_train_model.py",
        "4th_step4_generate_entry_like.py",
        "4th_step5_predict_rank.py",
    ], start=1):
        print(f"\n🚀 Step{i}: 実行中（本日データ）: {step}")
        try:
            subprocess.run(
                ["python", f"scripts/4th/{step}", "--date", today],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"❌ エラーが発生しました: {step}")
            return

    # Step 8 for today
    print(f"\n📤 Step8: 実行中: 4th_step8_generate_final_prediction_niren.py")
    try:
        subprocess.run(
            ["python", "scripts/4th/4th_step8_generate_final_prediction_niren.py", "--date", today],
            check=True
        )
    except subprocess.CalledProcessError:
        print("❌ エラーが発生しました: 4th_step8_generate_final_prediction_niren.py")

def main():
    today_date = datetime.today().date()
    yesterday_date = today_date - timedelta(days=1)
    run_daily_prediction(str(today_date), str(yesterday_date))

if __name__ == "__main__":
    main()