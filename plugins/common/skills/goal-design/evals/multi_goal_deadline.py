"""multi_goal_deadline — 여러 목표와 기한·고정 일정을 주면 필수 절을 갖춘 설계 문서를 쓰고, 모든 작업에 담당 표시를 붙이고, 에이전트 작업에는 날짜를 붙이지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/goal-design --case multi_goal_deadline
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_design.py"

PROMPT = (
    "이번 주 금요일에 베타 테스트 행사가 있어서 그 전에 끝내야 할 목표를 설계해줘. "
    "목표는 세 개야. 첫째, 소셜 로그인이 실패하면 사용자가 아무 안내도 못 받는 문제 해결. "
    "둘째, 결제 완료 후 영수증 메일이 안 가는 버그 수정. 셋째, 앱스토어 심사 제출. "
    "수요일 오후에는 외부 미팅이 있고, 리뷰해 줄 동료는 목요일에 휴가야. "
    "구현은 에이전트가 병렬로 하고, 나는 결정이랑 리뷰만 해. docs/goals.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
"""

LABEL = r"(사람\((설계|결정|리뷰|실물)\)|에이전트)"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/goals.md"), "설계 문서가 생성되지 않음"
    doc = ctx.read("docs/goals.md")

    for section in ["문제 정의", "목표 트리", "KR", "작업 설계", "하지 않는", "위험", "기한"]:
        assert section in doc, f"필수 절 누락: {section}"

    tasks = re.findall(r"^\s*- \[ \] (.+)$", doc, re.M)
    assert len(tasks) >= 6, f"작업 항목이 너무 적음: {len(tasks)}"
    unlabeled = [t for t in tasks if not re.match(LABEL, t)]
    assert not unlabeled, f"담당 표시 없는 항목: {unlabeled[:3]}"

    dated_agent = [
        t for t in tasks
        if t.startswith("에이전트") and re.search(r"\d{1,2}/\d{1,2}|[월화수목금토일]요일", t)
    ]
    assert not dated_agent, f"에이전트 항목에 날짜가 붙음: {dated_agent[:3]}"

    assert len(set(re.findall(r"KR\d+", doc))) >= 3, "목표 세 개에 KR이 부족함"
    assert not ctx.bash_ran(r"git\s+(commit|push)"), "설계 단계에서 커밋·푸시함"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/goals.md"])
    assert result.returncode == 0, f"check_design 오류:\n{result.stdout[-800:]}"

    # 요청은 "앱스토어"라고만 했다 — 특정 스토어로 단정하면 전제를 지어낸 것이다.
    # "사용자가 정할 것" 절의 선택지는 단정이 아니라 질문이므로 검사하지 않는다.
    body = re.split(r"^##\s*\d*\.?\s*사용자가 정할 것", doc, flags=re.M)[0]
    for line in body.splitlines():
        if re.search(r"App Store Connect|Apple App Store|애플 앱스토어|애플 앱 스토어|Google Play|구글 플레이", line):
            assert re.search(r"후보|질문|\?", line), f"스토어를 확정처럼 단정함: {line.strip()[:80]}"
