"""경로 해석 — 스킬 폴더 안의 자산 위치만 정한다.

작업 대상 레포와 사이클 폴더는 저장소마다 다르므로 상수로 두지 않는다. 사이클 폴더는
명령 인자로 받고, 작업 레포 경로는 사이클 머리말(`repo`)이 정한다. 그래서 이 스크립트는
설치 캐시에서 실행해도 같은 결과를 낸다.
"""

from __future__ import annotations

from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_HANDOFF = SKILL_DIR / "assets" / "cycle-template" / "handoff.md"
