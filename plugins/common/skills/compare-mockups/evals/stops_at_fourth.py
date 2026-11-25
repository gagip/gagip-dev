"""stops_at_fourth — 같은 질문의 시안을 세 번 안에 못 골랐으면 네 번째를 그리지 않고 탐색으로 돌린다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/compare-mockups --case stops_at_fourth
"""

import re

PROMPT = (
    "mockups 폴더의 첫 화면 시안 다 별로야. 같은 질문으로 안 두 개 시안 다시 그려줘. mockups/에 저장해."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p product/features/home mockups
cat > product/PRODUCT.md <<'MD'
# 할 일 앱
대상 사용자: 하루 할 일을 휴대폰으로 확인하는 사람
핵심 가치: 오늘 할 일을 바로 안다
비목표: 팀 협업
MD
cat > product/features/home/SPEC.md <<'MD'
상태: 시안
크기: 신규

문제: 앱을 열고 오늘 할 일을 찾는 데 오래 걸림. 근거: 사용자 관찰 2건
화면이 답할 질문: 오늘 할 일과 이번 주 흐름 중 무엇을 먼저 보여 줄까?
위험한 가정: 사용자는 오늘 것부터 본다. 관찰 2건으로 확인 중

결정 이력
- 시안 1번: 안 2개, 고르지 못함 (mockups/1.html)
- 시안 2번: 안 3개, 고르지 못함 (mockups/2.html)
- 시안 3번: 탐색용 안 2개, 고르지 못함 (mockups/3.html)
MD
for n in 1 2 3; do echo "<html lang=ko><body>시안 $n번</body></html>" > mockups/$n.html; done
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    files = sorted(ctx.sh("find . -name '*.html'").stdout.split())
    assert files == ["./mockups/1.html", "./mockups/2.html", "./mockups/3.html"], f"네 번째 시안을 그림: {files}"
    assert re.search(r"세 번|3번|3회|네 번째|3/3", ctx.final_text), "세 번 제한을 밝히지 않음"
    assert "탐색" in ctx.final_text, "탐색으로 돌아간다고 말하지 않음"
    spec = ctx.read("product/features/home/SPEC.md")
    assert re.search(r"^상태\s*:\s*탐색", spec, re.M), "SPEC.md 상태를 탐색으로 바꾸지 않음"
