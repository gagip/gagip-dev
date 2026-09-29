"""multi_goal_deadline — 문제 정의·설계와 기한·고정 일정·부재를 주면, 모든 작업에 담당과 대응 대상을 붙이고,
에이전트 작업에는 날짜를 붙이지 않고, 세 문서 정합성 검사를 통과하고, 승인 전이라 초안으로 남기는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case multi_goal_deadline
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_plan.py"

PROMPT = (
    "docs/problem.md와 docs/design.md를 바탕으로 플랜 짜줘. 이번 주 금요일에 베타 테스트 행사가 있어서 그 전에 "
    "끝내야 해. 수요일 오후에는 외부 미팅이 있고, 리뷰해 줄 동료는 목요일에 휴가야. "
    "구현은 에이전트가 병렬로 하고, 나는 결정이랑 리뷰만 해. docs/plan.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
cat > docs/problem.md <<'MD'
# 베타 전 정리 문제 정의

- 작성: 2026-09-28
- 원천: 사용자 요청

## 1. 문제 정의

### O1. 소셜 로그인이 실패해도 사용자가 다음 행동을 안다

| 칸 | 내용 |
|---|---|
| 지금 상태 | 실패하면 아무 안내 없이 로그인 화면에 머문다 |
| 이룰 상태 | 실패 경로마다 무엇을 하면 되는지 안내가 뜬다 |
| 왜 | 베타 참가자가 로그인에서 막히면 테스트 자체가 안 된다 (원천: 사용자 요청) |
| 범위 밖 | 이메일 로그인 |

### O2. 결제한 사용자가 영수증을 받는다

| 칸 | 내용 |
|---|---|
| 지금 상태 | 결제 완료 뒤 영수증 메일이 가지 않는다 |
| 이룰 상태 | 결제 완료마다 영수증 메일이 간다 |
| 왜 | 영수증이 없으면 결제 문의가 몰린다 (원천: 사용자 요청) |
| 범위 밖 | 환불 메일 |

### O3. 베타 빌드가 앱스토어 심사에 들어가 있다

| 칸 | 내용 |
|---|---|
| 지금 상태 | 심사에 제출한 빌드가 없다 |
| 이룰 상태 | 심사 대기 상태의 빌드가 있다 |
| 왜 | 행사 참가자가 설치할 수 있어야 한다 (원천: 사용자 요청) |
| 범위 밖 | 정식 출시 |

## 2. 목표 트리

O1. 소셜 로그인이 실패해도 사용자가 다음 행동을 안다
 └ O1.1 실패 경로마다 안내가 뜬다
O2. 결제한 사용자가 영수증을 받는다
 └ O2.1 결제 완료마다 영수증 메일이 발송된다
O3. 베타 빌드가 앱스토어 심사에 들어가 있다
 └ O3.1 심사 대기 빌드가 있다

## 3. 판정 기준 (OKR)

| Objective | KR | 판정 기준 | 판정 방법 | 판정 시점 | 유형 |
|---|---|---|---|---|---|
| O1.1 | KR1 | 실패 경로마다 안내 문구가 표시된다 | 확인 | 구현 후 | 약속 |
| O2.1 | KR1 | 테스트 결제 뒤 영수증 메일이 도착한다 | 확인 | 구현 후 | 약속 |
| O3.1 | KR1 | 심사 콘솔에 심사 대기 빌드가 보인다 | 사람 판정 | 제출 후 | 약속 |

## 4. 사용자가 정할 것

1. 대상 스토어 (후보: iOS만 / 두 스토어 모두)
MD
cat > docs/design.md <<'MD'
# 베타 전 정리 설계

- 작성: 2026-09-29
- 문제 정의: docs/problem.md
- 상태: 확정

## 1. 요구사항

| # | 결정 | 이유 | KR |
|---|---|---|---|
| D1 | 로그인 실패 코드를 `LoginError` 하나로 모아 화면에서 문구로 바꾼다 | 화면마다 흩어진 분기를 한 곳에서 다룬다 | O1.1 KR1 |
| D2 | 영수증 메일은 결제 완료 웹훅에서 큐에 넣어 보낸다 | 지금은 결제 화면이 닫히면 발송이 끊긴다 | O2.1 KR1 |
| D3 | 베타 빌드는 기존 릴리스 파이프라인의 베타 채널로 만든다 | 서명·버전 관리를 새로 만들지 않는다 | O3.1 KR1 |

## 2. 제약

- **서버 배포는 하루 한 번** — 영수증 수정은 배포 시점에 맞춰야 한다

## 3. 기술 리스크 / 선행 검증

- 없음

## 4. 미해결 설계 사안

- 없음
MD
"""

LABEL = r"(사람\((설계|결정|리뷰|실물)\)|에이전트)"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert "EnterPlanMode" not in ctx.tool_names(), "계획 모드에 들어감 — 플랜은 계획 모드 없이 문서로 쓴다"
    assert ctx.exists("docs/plan.md"), "플랜 문서가 생성되지 않음"
    doc = ctx.read("docs/plan.md")

    tasks = re.findall(r"^\s*- \[ \] (.+)$", doc, re.M)
    assert len(tasks) >= 6, f"작업 항목이 너무 적음: {len(tasks)}"
    unlabeled = [t for t in tasks if not re.match(LABEL, t)]
    assert not unlabeled, f"담당 표시 없는 항목: {unlabeled[:3]}"
    dated_agent = [
        t for t in tasks
        if t.startswith("에이전트") and re.search(r"\d{1,2}/\d{1,2}|[월화수목금토일]요일", t.split("←")[0])
    ]
    assert not dated_agent, f"에이전트 항목에 날짜가 붙음: {dated_agent[:3]}"

    assert re.search(r"기한", doc), "기한이 있는데 기한 판정이 없음"
    assert re.search(r"상태\s*:\s*초안", doc), "사용자 승인 전인데 상태가 초안이 아님"
    assert not re.search(r"^##(?!#).*(판정 기준|요구사항|목표 트리)", doc, re.M), "문제 정의·설계의 절을 다시 씀"
    assert not ctx.bash_ran(r"git\s+(commit|push)"), "플랜 단계에서 커밋·푸시함"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/plan.md",
                     "--design", "docs/design.md", "--problem", "docs/problem.md"])
    assert result.returncode == 0, f"check_plan 오류:\n{result.stdout[-800:]}"

    # 문제 정의는 대상 스토어를 사용자에게 물었다 — 플랜이 특정 스토어로 단정하면 전제를 지어낸 것이다.
    body = re.split(r"^##\s*\d*\.?\s*사용자가 정할 것", doc, flags=re.M)[0]
    for line in body.splitlines():
        if re.search(r"App Store Connect|Apple App Store|애플 앱스토어|애플 앱 스토어|Google Play|구글 플레이", line):
            assert re.search(r"후보|질문|\?|/", line), f"스토어를 확정처럼 단정함: {line.strip()[:80]}"
