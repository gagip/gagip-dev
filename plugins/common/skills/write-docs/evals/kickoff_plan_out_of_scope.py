"""kickoff_plan_out_of_scope — 착수 합의용 계획서 요청에 이 스킬이 발동하지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/write-docs --case kickoff_plan_out_of_scope
"""

PROMPT = "settings.py의 저장 버튼이 두 번 눌리는 버그 고치는 작업 계획서 써줘. 구현은 아직 하지 마. docs/계획.md에 저장해줘."

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > settings.py <<'PY'
saved = []


def save_settings(values):
    saved.append(dict(values))
PY
git add -A && git commit -qm init
"""


def check(ctx):
    assert not ctx.skill_fired(), f"착수 합의용 계획서에 발동함: {ctx.skill_invocations()}"
    assert ctx.exists("docs/계획.md"), "계획서가 생성되지 않음"
