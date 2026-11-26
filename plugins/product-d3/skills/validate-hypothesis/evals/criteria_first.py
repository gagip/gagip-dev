"""criteria_first — 실험 설계 요청에는 판정선을 EXPERIMENTS.md에 먼저 적고 결과를 채우지 않는다."""
import re

PROMPT = "음성으로 장보기 항목을 넣으면 입력이 빨라진다는 가정, 실험 설계해줘."
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && " + "cat > PRODUCT.md <<'MD'\n# 장보기 메모\n\n## Purpose\n혼자 사는 사람이 장보기 목록을 잊지 않게 한다.\n\n## Target Users\n혼자 사는 직장인\n\n## Core Problems\n퇴근길에 살 것을 잊는다.\n\n## Vision\n필요한 순간에 목록이 떠오른다.\n\n## Principles\n빠른 입력과 기능 수가 갈리면 빠른 입력.\n\n## Non-goals\n- 소셜 피드·친구 기능은 하지 않는다.\n- 경쟁·랭킹 요소는 넣지 않는다.\n\n## Success Criteria\n기준값을 잰 뒤 정함\nMD\n" + "mkdir -p src && printf 'items = []\n' > src/app.py && git add -A && git commit -qm init"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    log = ctx.read("**/EXPERIMENTS.md")
    assert log, "EXPERIMENTS.md가 없음"
    # 판정선 줄의 나머지와 그 아래 들여쓴 하위 줄까지가 판정선 값이다.
    block = re.search(r"판정선[ \t]*[:：]([^\n]*(?:\n[ \t]+[^\n]*)*)", log)
    value = re.sub(r"<!--.*?-->", "", block.group(1), flags=re.S).strip() if block else ""
    assert value, "판정선을 적지 않음"
    assert not re.search(r"판정\s*[:：]\s*(통과|실패)", log), "실행 전에 판정을 채움"
    assert ctx.sh("git status --porcelain -- src").stdout.strip() == "", "실험 설계에 제품 코드를 바꿈"
