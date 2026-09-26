from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path


PUBLIC01_FINAL_DIR = Path("tmp/public01/car7/latest/final")
PUBLISH_FINAL_DIR = Path("docs/public/latest/car7")

# car7本番公開で更新する範囲。
# archive全体 / profit全体を丸ごとstageしない。
BASE_ADD_PATHS = [
    PUBLISH_FINAL_DIR,
    Path("docs/public/profit/car7/index.html"),
    Path("docs/public/archive/car7/index.html"),
]


def get_publish_paths() -> list[Path]:
    paths = list(BASE_ADD_PATHS)

    latest_json = PUBLISH_FINAL_DIR / "latest.json"
    if latest_json.exists():
        try:
            data = json.loads(latest_json.read_text())
            publish_date = str(data.get("date", "")).strip()

            if publish_date:
                paths.append(
                    Path("docs/public/archive/car7") / publish_date
                )
        except Exception as exc:
            print(f"⚠️ failed to read car7 latest date: {exc}")

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


def wait_for_git_available(
    max_wait_seconds: int = 900,
    interval_seconds: int = 15,
) -> None:
    lock_path = Path(".git/index.lock")
    start = time.time()

    def git_process_running() -> bool:
        try:
            result = subprocess.run(
                [
                    "pgrep",
                    "-fl",
                    r"git (add|commit|push)|ssh git@github.com|git@github.com",
                ],
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
            return

        elapsed = int(time.time() - start)

        if elapsed >= max_wait_seconds:
            raise TimeoutError(
                f"git is still busy after {max_wait_seconds}s: "
                f"index_lock={lock_exists}, git_busy={git_busy}"
            )

        print(
            f"⏳ waiting for git available... "
            f"elapsed={elapsed}s "
            f"index_lock={lock_exists} "
            f"git_busy={git_busy}"
        )
        time.sleep(interval_seconds)


def sync_final() -> None:
    if not PUBLIC01_FINAL_DIR.exists():
        raise FileNotFoundError(
            f"public01 car7 final not found: {PUBLIC01_FINAL_DIR}"
        )

    if PUBLISH_FINAL_DIR.exists():
        shutil.rmtree(PUBLISH_FINAL_DIR)

    PUBLISH_FINAL_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PUBLIC01_FINAL_DIR, PUBLISH_FINAL_DIR)

    print(
        f"✅ synced car7 final: "
        f"{PUBLIC01_FINAL_DIR} -> {PUBLISH_FINAL_DIR}"
    )


def existing_publish_paths() -> list[str]:
    return [
        str(path)
        for path in get_publish_paths()
        if path.exists()
    ]


def stage_car7_only() -> None:
    wait_for_git_available()

    paths = existing_publish_paths()

    if not paths:
        raise RuntimeError("car7 publish target does not exist")

    # docs/public はgitignore対象なので -f が必要。
    # .DS_Store は公開対象にしない。
    run(
        [
            "git",
            "add",
            "-f",
            "--",
            *paths,
            ":(exclude)**/.DS_Store",
        ],
        check=True,
    )

    staged = run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "--",
            *paths,
        ],
        check=True,
    ).stdout.splitlines()

    print(f"✅ staged car7 publish targets: {len(staged)} files")


def has_car7_staged_diff() -> bool:
    paths = existing_publish_paths()

    if not paths:
        return False

    result = run(
        [
            "git",
            "diff",
            "--cached",
            "--quiet",
            "--",
            *paths,
        ]
    )
    return result.returncode != 0


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("=" * 72)
    print("🚀 START public01 car7 git publish")
    print("=" * 72)

    sync_final()
    stage_car7_only()

    if not has_car7_staged_diff():
        print("⏭️ no car7 changes. skip commit/push.")
        return 0

    message = f"update public01 car7 {now}"
    paths = existing_publish_paths()

    # car7公開対象だけcommitする。
    # 他作業でstage済みのファイルは巻き込まない。
    run(
        ["git", "commit", "-m", message, "--", *paths],
        check=True,
    )
    run(["git", "push", "origin", "main"], check=True)

    print("🎉 END public01 car7 git publish")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"❌ car7 git publish failed: {exc}")
        sys.exit(1)
