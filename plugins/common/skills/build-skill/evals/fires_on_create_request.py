"""fires_on_create_request — 스킬을 만들어 달라는 요청에 발동하고, 만든 스킬이 구조 린트를 통과한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import lint_skill  # noqa: E402

PROMPT = (
    "PR 설명을 매번 요약, 변경점, 테스트 방법 순서로 쓰고 있어. 이 워크플로를 스킬로 만들어줘. "
    "이름은 pr-description이고, 질문 없이 SKILL.md 초안까지 바로 만들어줘."
)
RUNS = 3


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"

    created = sorted(ctx.workdir.glob("**/SKILL.md"))
    assert created, f"SKILL.md가 만들어지지 않았다 / 툴: {ctx.tool_names()}"

    for skill_md in created:
        problems = lint_skill.lint(skill_md.parent)
        assert not problems, f"{skill_md.relative_to(ctx.workdir)} 린트 위반: {problems}"
