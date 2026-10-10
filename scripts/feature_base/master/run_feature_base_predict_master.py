#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = PROJECT_ROOT / "scripts" / "feature_base" / "master"
WORK_DIR = PROJECT_ROOT / "data" / "feature_base" / "work"
OUT_DIR = PROJECT_ROOT / "data" / "feature_base" / "master"

STEP02B_OUT = WORK_DIR / "step02b_predict_base_latest.csv"
STEP02_COMPAT = WORK_DIR / "step02a_base_with_results_latest.csv"

STEPS = [
    "step01_build_base.py",
    "step02b_predict_base.py",
    "step03_build_race_structure.py",
    "step04_build_area_features.py",
    "step05_build_line_position.py",
    "step06_feature_racer_history_windows.py",
    "step07_feature_racer_recent.py",
    "step08_feature_line_strength.py",
    "step09_feature_racer_tactic.py",
    "step10_feature_racer_shb.py",
    "step11_feature_race_summary.py",
    "build_feature_master.py",
]


def date_range(start: str, end: str) -> list[str]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    if e < s:
        raise ValueError("--end must be greater than or equal to --start")

    days = []
    cur = s
    while cur <= e:
        days.append(cur.isoformat())
        cur += timedelta(days=1)
    return days


def run_script(script: str, target_date: str) -> None:
    path = SCRIPT_DIR / script
    if not path.exists():
        raise FileNotFoundError(path)

    cmd = [sys.executable, str(path), "--date", target_date]

    if script == "build_feature_master.py":
        cmd.extend(["--mode", "predict"])

    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def promote_step02b_to_compat() -> None:
    if not STEP02B_OUT.exists():
        raise FileNotFoundError(STEP02B_OUT)

    shutil.copy2(STEP02B_OUT, STEP02_COMPAT)
    print(f"[OK] step02b promoted -> {STEP02_COMPAT}")


def run_one_day(target_date: str) -> None:
    print("")
    print("############################################################")
    print(f"# feature_base predict master RUN START date={target_date}")
    print("############################################################")

    # step01
    run_script("step01_build_base.py", target_date)

    # step02b
    run_script("step02b_predict_base.py", target_date)

    # 既存step03以降は step02a_base_with_results_latest.csv を読むため互換コピーする
    promote_step02b_to_compat()

    for script in STEPS[2:]:
        run_script(script, target_date)

    print("############################################################")
    print(f"# feature_base predict master RUN END date={target_date}")
    print("############################################################")
    print("")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="YYYY-MM-DD")
    group.add_argument("--start", help="YYYY-MM-DD")
    parser.add_argument("--end", help="YYYY-MM-DD。--start 使用時は必須")
    args = parser.parse_args()

    if args.date:
        targets = [args.date]
    else:
        if not args.end:
            raise SystemExit("--start を使う場合は --end も指定してください")
        targets = date_range(args.start, args.end)

    for d in targets:
        run_one_day(d)


if __name__ == "__main__":
    main()
