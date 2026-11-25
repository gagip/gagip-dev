"""product_direction — 기능이 방향에 맞는지 묻는 요청에 열리고 방향 문서와 대조하며 파일을 만들지 않는다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/grill --case product_direction
"""

import re

PROMPT = "팀원끼리 할 일을 나누는 기능을 넣고 싶은데 우리 제품 방향에 맞아? 할지 말지 정하자."
RUNS = 3
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p product
cat > product/PRODUCT.md <<'MD'
# 할 일 앱
대상 사용자: 하루 할 일을 혼자 관리하는 사람
핵심 가치: 오늘 할 일을 바로 안다
비목표: 팀 협업과 공유
MD
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert re.search(r"비목표", ctx.final_text), "비목표와 대조하지 않음"
    assert "팀 협업" in ctx.final_text, "방향 문서의 문장을 근거로 들지 않음"
    assert re.search(r"보류|방향 변경", ctx.final_text), "보류·방향 변경으로 가르지 않음"
    assert ctx.git_status_clean(), "정하기 전에 파일을 만듦"
