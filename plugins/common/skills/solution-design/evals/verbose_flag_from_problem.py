"""verbose_flag_from_problem — 문제 정의 문서를 받아 설계를 쓰면, 계획 모드에 들어가지 않고, 결정마다 KR을 매달고, 문제·작업·검증을 다시 쓰지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/solution-design --case verbose_flag_from_problem
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_solution.py"

PROMPT = (
    "docs/problem.md 문제 정의를 바탕으로 설계 문서를 써줘. docs/design.md에 저장해줘. "
    "구현은 아직 하지 마."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs src
cat > src/cli.py <<'PY'
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    print(f"processing {args.path}")


if __name__ == "__main__":
    main()
PY
cat > docs/problem.md <<'MD'
# CLI 디버그 문제 정의

- 작성: 2026-09-30
- 원천: 사용자 요청

## 1. 문제 정의

### O1. 문제가 생겼을 때 사용자가 원인을 스스로 좁힌다

| 칸 | 내용 |
|---|---|
| 지금 상태 | src/cli.py는 처리 대상 경로 한 줄만 출력한다 |
| 이룰 상태 | 사용자가 원할 때만 처리 단계별 정보를 볼 수 있다 |
| 왜 | 오류 문의마다 재현을 요청해야 한다 (원천: 사용자 요청) |
| 범위 밖 | 로그 파일 보관 |

## 2. 목표 트리

O1. 문제가 생겼을 때 사용자가 원인을 스스로 좁힌다
 ├ O1.1 상세 정보를 켜고 끌 수 있다
 └ O1.2 기본 출력은 지금과 같다

## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 상세 모드를 켜면 처리 단계마다 한 줄 이상 추가 출력이 있다 | 확인 | 구현 후 | 약속 |
| O1.2 | KR1 | 상세 모드를 켜지 않으면 출력이 지금과 한 글자도 다르지 않다 | 확인 | 구현 후 | 약속 |

## 4. 사용자가 정할 것

1. 없음
MD
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert "EnterPlanMode" not in ctx.tool_names(), "계획 모드에 들어감 — 설계는 계획 모드 없이 문서로 쓴다"
    assert ctx.exists("docs/design.md"), "설계 문서가 생성되지 않음"
    doc = ctx.read("docs/design.md")

    assert re.search(r"^\|\s*D1\s*\|", doc, re.M), "결정 번호(D1) 표가 없음"
    assert "--verbose" in doc or "-v" in doc, "새 CLI 옵션(공개 인터페이스)이 결정 문장에 없음"
    assert not re.search(r"^\s*- \[[ xX]\] ", doc, re.M), "설계에 작업 체크박스가 있음 — 작업은 work-plan 몫"
    assert ctx.read("src/cli.py").count("verbose") == 0, "구현하지 말라고 했는데 코드를 고침"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/design.md", "--problem", "docs/problem.md"])
    assert result.returncode == 0, f"check_solution 오류:\n{result.stdout[-800:]}"
