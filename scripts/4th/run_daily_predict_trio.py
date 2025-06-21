import argparse
from datetime import datetime, timedelta
import subprocess

def run_steps_for_date(target_date: str, steps: list, label: str, date_label: str):
    print(f"\n📅 {target_date} の{label}を開始します")

    for i, step in enumerate(steps, 1):
        if "step6" in step:
            print(f"\n🔁 Step6: 実行中（昨日のデータ）: {step}")
        elif "step7" in step:
            print(f"\n🔁 Step7: 実行中（昨日のデータ）: {step}")
        else:
            step_no = step.split("_")[0].replace("4th", "").replace("step", "")
            print(f"\n🚀 Step{step_no}: 実行中（{date_label}）: {step}")

        try:
            subprocess.run(
                ["python", f"scripts/4th/{step}", "--date", target_date],
                check=True
            )
        except subprocess.CalledProcessError:
            print(f"❌ エラーが発生しました: {step}")
            break

def main():
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    # 昨日の振り返り処理（Step6, Step7）
    run_steps_for_date(str(yesterday), [
        "4th_step6_evaluate_prediction_trio.py",
        "4th_step7_feedback_train_data_trio.py"
    ], label="振り返り処理", date_label="昨日のデータ")

    # 今日の予測処理（Step1〜Step5）
    run_steps_for_date(str(today), [
        "4th_step1_generate_racer_stats.py",
        "4th_step2_generate_train_racer_level_trio.py",
        "4th_step3_train_model.py",
        "4th_step4_generate_entry_like.py",
        "4th_step5_predict_rank.py"
    ], label="予測処理", date_label="本日データ")

    # 今日の出力処理（Step8）
    print(f"\n📤 Step8: 実行中: 4th_step8_generate_final_prediction_trio.py")
    try:
        subprocess.run(
            ["python", "scripts/4th/4th_step8_generate_final_prediction_trio.py", "--date", str(today)],
            check=True
        )
    except subprocess.CalledProcessError:
        print("❌ エラーが発生しました: 4th_step8_generate_final_prediction_trio.py")

if __name__ == "__main__":
    main()