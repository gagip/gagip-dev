"""withholds_small_sample — 표본·기간이 성과 조건에 못 미치면 판단을 유보하고 성과 조건을 고치지 않는다."""

PROMPT = "공유 기능 출시했는데 성과 어때? 데이터는 obs.csv야. 유지할지 정하자."
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "" + "mkdir -p docs/features/share && cat > docs/features/share/PRD.md <<'MD'\n# share\n\n## Purpose\n같이 사는 사람과 목록을 함께 쓴다.\n\n## Problem\n같은 물건을 둘이 산다 (관찰: 인터뷰 5명 중 3명)\n\n## Scope\n목록 공유 링크\n\n## Success Criteria\n- 대상: 공유 링크를 받은 사용자\n- 관찰: 4주 안에 받은 목록에 항목을 하나 이상 추가한 비율\n- 성공: 30% 이상\n- 표본·기간: 받은 사용자 200명, 4주\n- 볼 날: 2026-12-20\nMD\n" + ""
    "printf 'user,received_at,added_items\\n' > obs.csv && "
    "for i in 1 2 3 4 5 6 7 8 9 10 11 12; do echo \"u$i,2026-11-20,$((i % 3))\" >> obs.csv; done && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"유보"), "표본이 모자란데 유보하지 않음"
    assert ctx.sh("git diff --quiet -- docs/features/share/PRD.md").returncode == 0, "결과를 보고 성과 조건을 고침"
