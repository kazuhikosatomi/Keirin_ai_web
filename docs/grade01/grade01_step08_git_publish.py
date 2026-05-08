

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
grade01_step08_git_publish.py

目的:
HTML更新後に GitHub へ自動反映する

対象:
- docs/grade/（HTMLのみを公開）

動作:
1. git add
2. 差分があれば commit
3. push
"""

from __future__ import annotations

import subprocess
from datetime import datetime


def run(cmd: list[str]):
    print("▶", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def has_diff() -> bool:
    result = run(["git", "status", "--porcelain"])
    return bool(result.stdout.strip())


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("=" * 72)
    print("🚀 START grade01 step08 git publish")
    print("=" * 72)

    # add
    run(["git", "add", "docs/grade"])

    # check diff
    if not has_diff():
        print("⏭️ no changes. skip commit.")
        print("=" * 72)
        return

    message = f"update grade01 {now}"

    # commit
    run(["git", "commit", "-m", message])

    # push
    run(["git", "push"])

    print("=" * 72)
    print("🎉 END grade01 step08 git publish")
    print("=" * 72)


if __name__ == "__main__":
    main()