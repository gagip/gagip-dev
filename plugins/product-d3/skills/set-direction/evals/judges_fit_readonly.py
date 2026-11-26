"""judges_fit_readonly — 방향 판정 요청에는 비목표를 근거로 보류·방향 변경을 권하고 파일을 바꾸지 않는다."""

PROMPT = "친구들 장보기 목록을 피드로 보는 기능 넣으려는데 우리 방향에 맞아?"
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "mkdir -p src && printf 'items = []\n' > src/app.py && git add -A && git commit -qm init"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"보류|방향 변경"), "보류·방향 변경을 권하지 않음"
    assert ctx.re_search(ctx.final_text, r"비목표|Non-goals|친구 기능"), "근거 문장을 대지 않음"
    assert ctx.git_status_clean(), "판정 요청에 파일을 바꿈"
