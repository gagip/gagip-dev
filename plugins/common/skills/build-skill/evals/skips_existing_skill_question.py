"""skips_existing_skill_question — 기존 스킬이 무엇인지 묻기만 하는 질문에는 build-skill이 열리지 않는다."""

PROMPT = "skills/standup-notes/SKILL.md는 어떤 스킬이야? 한 줄로만 설명해줘."
RUNS = 3
SCAFFOLD = r"""
mkdir -p skills/standup-notes
cat > skills/standup-notes/SKILL.md <<'EOF'
---
name: standup-notes
description: 어제 한 일, 오늘 할 일, 막힌 점을 스탠드업 형식으로 정리한다.
---

# Standup Notes

어제·오늘·막힌 점 세 항목으로 정리한다.
EOF
"""


def check(ctx):
    assert not ctx.skill_fired(), f"질문인데 발동: {ctx.skill_invocations()}"
    assert not ctx.tool_used("Write") and not ctx.tool_used("Edit"), "질문인데 파일을 수정했다"
