"""three_variants_with_brief — 기획서가 있으면 단일 시안이 아니라 복수 변형을 시도하는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/mockup-review --case three_variants_with_brief
"""

PROMPT = "screen-brief.md에 정리된 '알림 설정 화면' 시안 만들어줘."

RUNS = 3

SCAFFOLD = r"""
cat > screen-brief.md <<'EOF'
## 알림 설정 화면

- 타겟: 하루에 알림을 10개 이상 받는 파워유저
- 문제: 중요한 알림과 스팸성 알림이 섞여서 중요한 걸 놓친다
- 목적: 중요한 알림을 놓치지 않게 종류별로 켜고 끌 수 있게 한다
- 성공 기준: 중요 알림 도달률 개선
- 실패 조건: 설정이 복잡해서 아무도 안 쓴다
- 사용자 시나리오: 사용자가 알림 종류별로 on/off를 토글하고 저장한다
- 요구사항 (필수): 종류별 토글, 저장 버튼
- 제외 항목: 알림 우선순위 커스텀 정렬
EOF
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"

    write_targets = [
        tc["input"].get("file_path", "")
        for tc in ctx.tool_calls
        if tc["name"] in ("Write", "Edit")
    ]
    variant_targets = {p for p in write_targets if p and "screen-brief.md" not in p}
    assert len(variant_targets) >= 3, (
        f"시안 파일이 3개 미만으로 생성됨: {sorted(variant_targets)}"
    )

    assert ctx.tool_used("Agent") or ctx.tool_used("Task"), (
        "분리 세션(서브에이전트) 비평을 시도하지 않음: " + str(ctx.tool_names())
    )
