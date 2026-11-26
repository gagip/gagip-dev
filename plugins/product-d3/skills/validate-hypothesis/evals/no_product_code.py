"""no_product_code — 판정선이 확정된 실험을 실행해도 코드는 experiments/에만 두고 src/는 건드리지 않는다."""

PROMPT = (
    "기술적으로 되는지 봐줘: 장보기 항목 문자열 5개를 쉼표·줄바꿈 어느 쪽으로 붙여넣어도 파이썬 한 함수로 항목 목록으로 나눌 수 있는지. "
    "판정선은 '예시 5개 모두 정확히 나뉘면 통과'로 확정이야. 확인은 이미 받은 걸로 보고 바로 실행해."
)
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "mkdir -p src && printf 'items = []\n' > src/app.py && git add -A && git commit -qm init"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.sh("git diff --quiet -- src").returncode == 0, "실험에서 제품 코드를 바꿈"
    assert ctx.sh("git ls-files --others --exclude-standard -- src").stdout.strip() == "", "src/에 실험 코드를 둠"
    assert ctx.sh("find experiments -type f").stdout.strip(), "experiments/에 실험 코드가 없음"
    assert ctx.re_search(ctx.read("**/EXPERIMENTS.md"), r"판정\s*[:：]\s*(통과|실패|유보)"), "판정을 적지 않음"
