"""basic_brief — 기획서 요청 시 스킬이 발동하고 필수 섹션을 전부 갖춘 문서를 만드는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/screen-brief --case basic_brief
"""

PROMPT = (
    "새 화면 기획서를 정리하고 싶어. 화면 이름은 '알림 설정 화면'이야. "
    "타겟은 하루에 알림을 10개 이상 받는 파워유저, 문제는 중요한 알림과 스팸성 알림이 섞여서 "
    "중요한 걸 놓친다는 거야. 성공 기준은 중요 알림 도달률 개선, 실패 조건은 설정이 복잡해서 "
    "아무도 안 쓰는 것. 시나리오는 사용자가 알림 종류별로 on/off를 토글하고 저장하는 흐름이야. "
    "필수 요구사항은 종류별 토글과 저장 버튼, 제외 항목은 알림 우선순위 커스텀 정렬이야. "
    "docs/screen-brief.md 파일에 정리해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/screen-brief.md"), "기획서 파일이 생성되지 않음"

    doc = ctx.read("docs/screen-brief.md")
    required_labels = [
        "타겟", "문제", "목적", "성공 기준", "실패 조건",
        "사용자 시나리오", "요구사항", "제외 항목",
    ]
    missing = [label for label in required_labels if label not in doc]
    assert not missing, f"필수 섹션 누락: {missing}\n---\n{doc}"
