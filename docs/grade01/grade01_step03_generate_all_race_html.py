#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
step43 のCSVから、全レース分の rXX.html を生成する
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import subprocess

DEFAULT_DATE = "2026-04-26"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--top-exacta", type=int, default=5)
    parser.add_argument("--top-trifecta", type=int, default=10)
    parser.add_argument("--top-trio", type=int, default=5)
    return parser.parse_args()


def load_step43(date: str) -> pd.DataFrame:
    path = Path(f"data/sim06/step43/sim06_step43_all_top_tickets_{date}.csv")
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("step43 is empty")
    return df


def parse_race_id(race_id: str):
    parts = str(race_id).split("_")
    venue_id = parts[1]
    race_no = parts[2].replace("R", "")
    return venue_id, race_no


def main():
    args = parse_args()

    print("=" * 72)
    print(f"🚀 START step03 generate all race html | date={args.date}")
    print("=" * 72)

    df = load_step43(args.date)

    race_ids = sorted(df["race_id"].astype(str).unique())
    print(f"📊 races found: {len(race_ids)}")

    for race_id in race_ids:
        venue_id, race_no = parse_race_id(race_id)

        out_dir = Path(f"docs/grade/races/v{venue_id}")
        out_dir.mkdir(parents=True, exist_ok=True)

        output_path = out_dir / f"r{race_no}.html"

        print(f"▶ 生成: {race_id} → {output_path}")

        cmd = [
            "python3",
            "scripts/grade01/grade01_step01_generate_sample_race_html.py",
            "--date", args.date,
            "--race-id", race_id,
            "--top-exacta", str(args.top_exacta),
            "--top-trifecta", str(args.top_trifecta),
            "--top-trio", str(args.top_trio),
            "--output", str(output_path),
        ]

        subprocess.run(cmd, check=True)

    print("=" * 72)
    print("🎉 END step03 generate all race html")
    print("=" * 72)


if __name__ == "__main__":
    main()