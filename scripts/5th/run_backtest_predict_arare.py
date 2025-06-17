import argparse
from datetime import datetime, timedelta
import subprocess

steps = [
    "5th_step1_generate_racer_stats.py",
    "5th_step2_generate_train_racer_level_sanrentan.py",
    "5th_step3_train_model.py",
    "5th_step4_generate_entry_like.py",
    "5th_step5_predict_arare.py",
    "5th_step6_evaluate_prediction.py",
    "5th_step7_feedback_train_data.py",
]

def run_steps_for_date(target_date: str, end_date: str, is_first: bool):
    print(f"\n📅 {target_date} の処理を開始します")

    if is_first:
        print("\n🚀 Step0: 実行中: 5th_step0_generate_label_arare.py")
        try:
            subprocess.run(
                ["python", "scripts/5th/5th_step0_generate_label_arare.py", "--start", args.start, "--end", args.end],
                check=True
            )
        except subprocess.CalledProcessError:
            print("❌ エラーが発生しました: 5th_step0_generate_label_arare.py")
            return

    for i, step in enumerate(steps, start=1):
        print(f"\n🚀 Step{i}: 実行中: {step}")
        try:
            subprocess.run(
                ["python", f"scripts/5th/{step}", "--date", target_date],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"❌ エラーが発生しました: {step}")
            break

        if step == "5th_step5_predict_arare.py" and target_date == end_date:
            print("✅ 最終日のため Step6/7 をスキップします")
            break

    if target_date == end_date:
        print(f"\n🚀 Step8: 実行中: 5th_step8_generate_final_prediction.py")
        try:
            subprocess.run(
                ["python", "scripts/5th/5th_step8_generate_final_prediction.py", "--date", target_date],
                check=True
            )
        except subprocess.CalledProcessError:
            print("❌ エラーが発生しました: 5th_step8_generate_final_prediction.py")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="終了日 (YYYY-MM-DD)")
    global args
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    current_date = start_date
    is_first = True
    while current_date <= end_date:
        run_steps_for_date(str(current_date), str(end_date), is_first)
        is_first = False
        current_date += timedelta(days=1)

if __name__ == "__main__":
    main()