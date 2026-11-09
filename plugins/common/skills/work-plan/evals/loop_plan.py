"""loop_plan — 고치고 검토받고 다시 고치는 작업이면 계획서에 「한 회차」·「루프 장치」 절을 넣고,
회차 상한·확정 목록·심각도 근거·끝 검토를 장치로 두며, 실제 검토·수정은 시작하지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case loop_plan
"""

import re

PROMPT = (
    "docs/guide.md 사용자 안내서의 영어 문장을 원어민 기준으로 다듬으려고 해. 서브에이전트 검토자에게 보이고, "
    "지적을 반영하고, 다시 검토받는 걸 몇 번 돌릴 거야. 목표랑 완료 기준을 정하고 루프로 돌릴 계획서를 "
    "docs/계획.md에 써줘. 검토나 수정은 아직 하지 마."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p docs
cat > docs/guide.md <<'MD'
# Getting Started

Please to open the app and doing the Sign In.
When error is occurred, you can retry it again.
Your datas is saved automatically on the server.
MD
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/계획.md"), "계획서가 생성되지 않음"
    doc = ctx.read("docs/계획.md")

    for section in ("한 회차", "루프 장치"):
        assert re.search(r"^#+\s*" + section, doc, re.M), f"루프 절 누락: {section}"
    assert re.search(r"(회차\s*상한|최대\s*\d\s*회|상한\s*\d)", doc), "회차 상한이 없음"
    assert "확정 목록" in doc, "앞 회차에 바꾼 것을 지키는 확정 목록이 없음"
    assert re.search(r"근거", doc) and re.search(r"중간", doc), "중간 지적의 근거 요구가 없음"
    assert re.search(r"끝\s*검토|전체\s*diff|전체를\s*다시", doc), "루프 단위 밖을 보는 끝 검토가 없음"

    changed = [ln[3:].strip('"') for ln in ctx.sh("git status --porcelain -uall").stdout.splitlines()]
    assert "docs/guide.md" not in changed, "계획 단계인데 안내서를 고침"
