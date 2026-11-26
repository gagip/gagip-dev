"""defect_before_direction — 성과가 낮아도 동작 결함 근거가 있으면 방향 변경 대신 버그 수정으로 분류한다."""

PROMPT = "공유 기능 성과가 목표의 절반도 안 나왔어. 방향 바꿔야 할까? 버그 보고는 reports.md에 있어."
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "" + "mkdir -p docs/features/share && cat > docs/features/share/PRD.md <<'MD'\n# share\n\n## Purpose\n같이 사는 사람과 목록을 함께 쓴다.\n\n## Problem\n같은 물건을 둘이 산다 (관찰: 인터뷰 5명 중 3명)\n\n## Scope\n목록 공유 링크\n\n## Success Criteria\n- 대상: 공유 링크를 받은 사용자\n- 관찰: 4주 안에 받은 목록에 항목을 하나 이상 추가한 비율\n- 성공: 30% 이상\n- 표본·기간: 받은 사용자 200명, 4주\n- 볼 날: 2026-12-20\nMD\n" + ""
    "printf '# 버그 보고\\n- 2026-11-21 공유 링크로 연 목록에서 추가 버튼을 눌러도 저장이 안 됨 (안드로이드 4건)\\n- 2026-11-22 같은 증상 2건 추가\\n' > reports.md && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"결함|버그 수정|Bug Fix"), "동작 결함으로 분류하지 않음"
    assert ctx.sh("git diff --quiet -- PRODUCT.md").returncode == 0, "방향 문서를 고침"
