import argparse
from datetime import datetime, timedelta
import subprocess

def run_command(step_name, date_arg=None, extra_args=None):
    print(f"\n🚀 {step_name} 実行中")
    cmd = ["python", f"scripts/5th/{step_name}"]
    if date_arg:
        cmd += ["--date", date_arg]
    if extra_args:
        cmd += extra_args
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"❌ エラーが発生しました: {step_name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=False, help="処理日 (YYYY-MM-DD、指定なしで今日)")
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target_date = datetime.today().date()
    prev_date = target_date - timedelta(days=1)

    print(f"\n📅 {target_date} の予測処理を開始します")

    # Step6・Step7（前日の振り返り）
    run_command("5th_step6_evaluate_prediction.py", date_arg=str(prev_date))
    run_command("5th_step7_feedback_train_data.py", date_arg=str(prev_date))

    # Step0〜Step5（本日の予測処理）
    run_command("5th_step0_generate_label_arare.py", extra_args=["--start", str(prev_date), "--end", str(prev_date)])
    run_command("5th_step1_generate_racer_stats.py", date_arg=str(target_date))
    run_command("5th_step2_generate_train_racer_level_sanrentan.py", date_arg=str(target_date))
    run_command("5th_step3_train_model.py", date_arg=str(target_date))
    run_command("5th_step4_generate_entry_like.py", date_arg=str(target_date))
    run_command("5th_step5_predict_arare.py", date_arg=str(target_date))

    # Step8（出力）
    run_command("5th_step8_generate_final_prediction.py", date_arg=str(target_date))

if __name__ == "__main__":
    main()