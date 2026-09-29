"""flags_overload — 사람이 정할 일이 많은 목표를 하루에 몰아넣으면, 기한 판정에서 들어가지 않는다고 밝히고
축소안을 내는지, 설계를 생략해도 작업을 KR에 직접 매다는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case flags_overload
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_plan.py"

PROMPT = (
    "docs/problem.md 목표들을 내일 하루 안에 끝내는 플랜 짜줘. 코드 작업이 아니라 설계 문서는 없어, 생략해. "
    "넷 다 내가 직접 정하고 검토해야 하는 일이고, 내일 오후 2시부터 5시까지는 회의가 있어. "
    "자료 조사나 초안은 에이전트가 해도 돼. docs/plan.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
cat > docs/problem.md <<'MD'
# 신규 서비스 출시 준비 문제 정의

- 작성: 2026-09-30
- 원천: 사용자 요청

## 1. 문제 정의

### O1. 신규 서비스를 외부에 설명할 수 있다

| 칸 | 내용 |
|---|---|
| 지금 상태 | 누구에게 얼마에 무엇을 약속하는지 정해진 것이 없다 |
| 이룰 상태 | 타겟·가격·문구·발표 자료가 정해져 있다 |
| 왜 | 투자자 발표와 랜딩 공개가 이 결정들에 걸려 있다 (원천: 사용자 요청) |
| 범위 밖 | 광고 집행 |

## 2. 목표 트리

O1. 신규 서비스를 외부에 설명할 수 있다
 ├ O1.1 타겟 고객이 정의돼 있다
 ├ O1.2 가격 정책이 정해져 있다
 ├ O1.3 랜딩 페이지 문구가 확정돼 있다
 └ O1.4 투자자 발표 자료가 완성돼 있다

## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 타겟 고객 정의 문서를 사용자가 승인했다 | 사람 판정 | 작성 후 | 약속 |
| O1.2 | KR1 | 가격표를 사용자가 승인했다 | 사람 판정 | 작성 후 | 약속 |
| O1.3 | KR1 | 랜딩 문구를 사용자가 확정했다 | 사람 판정 | 작성 후 | 약속 |
| O1.4 | KR1 | 발표 자료를 사용자가 최종본으로 확정했다 | 사람 판정 | 작성 후 | 약속 |

## 4. 사용자가 정할 것

1. 없음
MD
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/plan.md"), "플랜 문서가 생성되지 않음"
    doc = ctx.read("docs/plan.md")

    assert re.search(r"설계\s*:\s*생략", doc), "설계를 생략하라고 했는데 머리말에 생략이 없음"
    assert "기한" in doc, "기한 판정 절 누락"
    assert re.search(r"안 들어감|빠듯함", doc), "과부하인데 기한 판정이 모두 '들어감'"
    assert re.search(r"축소|제외|미루|옮기", doc), "들어가지 않는데 축소안이 없음"
    assert not re.search(r"^\s*- \[ \] .*\bD\d+\b", doc, re.M), "설계가 없는데 작업이 결정 번호를 가리킴"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/plan.md", "--problem", "docs/problem.md"])
    assert result.returncode == 0, f"check_plan 오류:\n{result.stdout[-800:]}"
