#!/usr/bin/env python3
"""Codex plugin validator를 git이 추적하는 파일만으로 실행한다.

validator는 git 무시 여부와 상관없이 디스크의 `skills/` 하위 폴더를 모두 스킬로 본다. 그래서
`<skill>-eval-runs/` 같은 로컬 평가 결과 폴더가 있으면 "missing SKILL.md"로 실패한다. 이 스크립트는
플러그인 폴더에서 git이 추적하는 파일만 임시 폴더로 복사해 validator를 돌린다 — 실제로 배포되는
내용과 같은 상태를 검증한다.

    python3 scripts/validate_codex_plugin.py plugins/<플러그인명>

종료 코드: validator 종료 코드를 그대로 돌려준다. validator가 설치돼 있지 않으면 3.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = Path(
    os.environ.get(
        "CODEX_PLUGIN_VALIDATOR",
        "~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py",
    )
).expanduser()
NOT_INSTALLED = 3


def tracked_files(plugin_dir: Path) -> list[Path]:
    rel = plugin_dir.resolve().relative_to(ROOT)
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", str(rel)],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [Path(p) for p in out.decode("utf-8").split("\0") if p]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    plugin_dir = (ROOT / sys.argv[1]).resolve() if not Path(sys.argv[1]).is_absolute() else Path(sys.argv[1])
    if not (plugin_dir / ".codex-plugin" / "plugin.json").is_file():
        print(f"플러그인 폴더가 아님: {sys.argv[1]}")
        return 2
    if not VALIDATOR.is_file():
        print(f"Codex validator 미설치: {VALIDATOR}")
        return NOT_INSTALLED

    files = tracked_files(plugin_dir)
    if not files:
        print(f"git이 추적하는 파일이 없음: {sys.argv[1]}")
        return 2

    with tempfile.TemporaryDirectory(prefix="codex-validate-") as tmp:
        for rel in files:
            src = ROOT / rel
            if not src.is_file():  # 추적 중이지만 워킹트리에서 지워진 파일
                continue
            dst = Path(tmp) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        target = Path(tmp) / plugin_dir.relative_to(ROOT)
        result = subprocess.run(
            ["uv", "run", "--with", "pyyaml", "python", str(VALIDATOR), str(target)],
        )
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
