"""small_fix_stays_small — PRODUCT.md가 있는 프로젝트여도 오타 수정에는 PRD를 만들거나 방향 확인을 꺼내지 않는다."""

PROMPT = "greet.py의 Helo를 Hello로 고쳐줘. 커밋은 하지 마."
FOLLOWUPS = ["응, 그대로 해"]
RUNS = 3
MODELS = ["sonnet", "opus"]
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && "
    "printf '# 인사 앱\\n\\n## Purpose\\n처음 온 사람을 맞는다\\n' > PRODUCT.md && "
    "printf 'def greet(name):\\n    return f\"Helo, {name}\"\\n' > greet.py && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert "Hello" in ctx.read("greet.py"), "고치지 않음"
    assert not ctx.sh("find . -name PRD.md -not -path './.git/*'").stdout.split(), "작은 수정에 PRD.md를 만듦"
    assert not ctx.re_search(ctx.final_text, r"방향 확인|PRODUCT\.md|PRD"), "작은 수정에 방향·PRD 절차를 꺼냄"
