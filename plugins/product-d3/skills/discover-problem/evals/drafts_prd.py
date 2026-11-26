"""drafts_prd — 근거가 있는 아이디어는 PRD 초안을 쓰고 다음 활동을 판정하며 제품 코드는 건드리지 않는다."""

PROMPT = "퇴근길에 장보기 목록 알림을 받고 싶다는 피드백이 3건 왔어(feedback.md). 이 기능 넣을 만해? 검토해서 PRD 초안까지 써줘. 묻지 말고 진행해."
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "mkdir -p src && printf 'items = []\n' > src/app.py && "
    "printf '# 피드백\\n- 2026-11-02 사용자A: 집에 와서야 우유 산다는 걸 떠올림\\n- 2026-11-05 사용자B: 마트 앞에서 알려주면 좋겠다\\n- 2026-11-09 사용자C: 목록을 열어볼 생각을 못 함\\n' > feedback.md && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    prds = ctx.sh("find docs/features -name PRD.md").stdout.split()
    assert prds, "PRD 초안이 없음"
    assert ctx.sh("git status --porcelain -- src").stdout.strip() == "", "탐색 단계에서 제품 코드를 바꿈"
    assert ctx.re_search(ctx.final_text, r"validate-hypothesis|deliver-work|보류"), "다음 활동과 맡을 곳을 판정하지 않음"
