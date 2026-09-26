#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
git_publish.py

目的:
grade05 のHTML生成・アーカイブ更新が一通り終わった後に、GitHub へまとめて反映する。

方針:
- build / watch / archive 系スクリプトでは git add / commit / push しない
- publish は最後にこのスクリプトを1回だけ実行する
- grade04 本番トップ docs/index.html は触らない
- grade05 確認用トップ docs/index_grade05.html は公開対象に含める

対象:
- docs/index_grade05.html
- tmp/public01/car9/latest/snapshot
- docs/public/latest/car9
- docs/public/archive
- docs/public/profit
"""

from __future__ import annotations

import subprocess
import time
import os
import sys
import shutil
import json
from datetime import datetime
from pathlib import Path


PUBLIC01_FINAL_DIR = Path("tmp/public01/car9/latest/final")
PUBLISH_FINAL_DIR = Path("docs/public/latest/car9")

BASE_ADD_PATHS = [
    PUBLISH_FINAL_DIR,
    Path("docs/public/site_state.json"),
    Path("docs/public/archive/car9/index.html"),
    Path("docs/public/profit/car9/index.html"),
]


def get_publish_paths() -> list[Path]:
    """car9 の現在公開に必要なファイルだけを返す。"""
    paths = list(BASE_ADD_PATHS)

    latest_json = PUBLISH_FINAL_DIR / "latest.json"
    if latest_json.exists():
        try:
            data = json.loads(latest_json.read_text())
            publish_date = str(data.get("date", "")).strip()

            if publish_date:
                paths.append(
                    Path("docs/public/archive/car9") / publish_date
                )
        except Exception as exc:
            print(f"⚠️ failed to read latest date: {exc}")

    return paths


def run(cmd: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    print("▶", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result


def has_diff() -> bool:
    result = run(["git", "status", "--porcelain"])
    return bool(result.stdout.strip())


def sync_public01_final() -> None:
    """public01/car9 の完成済み final を既存公開領域へ完全同期する。"""
    if not PUBLIC01_FINAL_DIR.exists():
        raise FileNotFoundError(
            f"public01 final not found: {PUBLIC01_FINAL_DIR}"
        )

    if PUBLISH_FINAL_DIR.exists():
        shutil.rmtree(PUBLISH_FINAL_DIR)

    PUBLISH_FINAL_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PUBLIC01_FINAL_DIR, PUBLISH_FINAL_DIR)

    print(
        f"✅ synced public01 final: "
        f"{PUBLIC01_FINAL_DIR} -> {PUBLISH_FINAL_DIR}"
    )


def add_publish_targets() -> None:
    add_paths = get_publish_paths()

    existing_paths = [str(path) for path in add_paths if path.exists()]
    missing_paths = [str(path) for path in add_paths if not path.exists()]

    if missing_paths:
        print("⚠️ missing publish targets:")
        for path in missing_paths:
            print(f"  - {path}")

    if not existing_paths:
        print("⚠️ no publish targets found. skip git add.")
        return

    wait_for_git_available()

    normal_paths = [
        path
        for path in existing_paths
        if not path.startswith("docs/public/")
    ]

    force_paths = [
        path
        for path in existing_paths
        if path.startswith("docs/public/")
    ]

    for path in normal_paths:
        run(
            ["git", "add", "--", path],
            check=True,
        )

    # docs/public はgitignore対象なので -f が必要。
    # 新規archiveを確実に拾うため、公開対象ごとに個別stageする。
    for path in force_paths:
        run(
            [
                "git",
                "add",
                "-f",
                "--",
                path,
            ],
            check=True,
        )



def wait_for_git_available(max_wait_seconds: int = 900, interval_seconds: int = 15) -> None:
    """他の公開系publishと衝突しないようにgit操作の空きを待つ。"""
    lock_path = Path(".git/index.lock")
    start = time.time()

    def git_process_running() -> bool:
        try:
            result = subprocess.run(
                ["pgrep", "-fl", r"git (add|commit|push)|ssh git@github.com|git@github.com"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return False

        current_pid = str(os.getpid())
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.split()[0] == current_pid:
                continue
            return True
        return False

    while True:
        lock_exists = lock_path.exists()
        git_busy = git_process_running()

        if not lock_exists and not git_busy:
            if time.time() - start > 0:
                print("✅ git available")
            return

        elapsed = int(time.time() - start)
        if elapsed >= max_wait_seconds:
            raise TimeoutError(
                f"git is still busy after {max_wait_seconds}s: "
                f"index_lock={lock_exists}, git_busy={git_busy}"
            )

        print(
            f"⏳ waiting for git available... "
            f"elapsed={elapsed}s index_lock={lock_exists} git_busy={git_busy}"
        )
        time.sleep(interval_seconds)


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("=" * 72)
    print("🚀 START public01 car9 publish git publish")
    print("=" * 72)

    print("📦 public01 final:")
    print(f"  source: {PUBLIC01_FINAL_DIR}")
    print(f"  publish: {PUBLISH_FINAL_DIR}")

    sync_public01_final()

    print("📦 publish targets:")
    for path in get_publish_paths():
        status = "OK" if path.exists() else "missing"
        print(f"  - {path} [{status}]")

    add_publish_targets()

    if not has_diff():
        print("⏭️ no changes. skip commit/push.")
        print("=" * 72)
        print("🎉 END public01 car9 publish git publish")
        print("=" * 72)
        return 0

    message = f"update public01 car9 {now}"

    run(["git", "commit", "-m", message], check=True)
    run(["git", "push"], check=True)

    print("=" * 72)
    print("🎉 END public01 car9 publish git publish")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("❌ git publish failed")
        print(f"command: {' '.join(exc.cmd)}")
        sys.exit(exc.returncode)
