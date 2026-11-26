"""holds_nongoal — 비목표와 부딪히는 아이디어는 보류를 권하고 PRD를 만들지 않는다."""

PROMPT = "사용자끼리 장보기 절약 랭킹을 겨루는 기능 해볼까?"
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "mkdir -p src && printf 'items = []\n' > src/app.py && git add -A && git commit -qm init"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"보류"), "보류를 권하지 않음"
    assert not ctx.sh("find . -name PRD.md -not -path './.git/*'").stdout.split(), "보류할 아이디어에 PRD를 만듦"
