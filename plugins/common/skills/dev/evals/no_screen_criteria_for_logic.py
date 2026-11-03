"""화면을 바꾸지 않는 요청이면 계획에 화면 기준을 만들지 않는다."""

PROMPT = """src/sum.py의 total()이 빈 리스트에서 에러 나는 걸 0을 돌려주게 고쳐줘. dev 스킬로 진행하고, 웹·외부에 올리지 마."""
RUNS = 1
SCAFFOLD = r"""
git init -q && git config user.email e@e.com && git config user.name E
mkdir -p src && printf 'def total(xs):\n    return xs[0] + sum(xs[1:])\n' > src/sum.py
git add -A && git commit -qm "chore: init"
"""


def plan_text(ctx):
    docs = [p.read_text(encoding="utf-8") for p in ctx.workdir.rglob("*.md") if ".git" not in p.parts]
    return "\n".join(docs + [ctx.final_text])


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert not ctx.re_search(plan_text(ctx), r"(?m)^\s*(#+|\*\*|[-*] \*\*)[^\n]*화면 기준"), "화면과 무관한 변경에 화면 기준 항목을 만듦"
