"""product_conditions — PRD의 범위·성공 기준이 빈 신규 기능은 구현하지 않고 빈칸을 보인다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/product-d3/skills/deliver-work --case product_conditions
"""

import re

PROMPT = "docs/features/carry/PRD.md 기능 구현해줘."
RUNS = 3
MODELS = ["sonnet", "opus"]
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p docs/features/carry
printf '# 할 일 앱\n\n## Target Users\n혼자 할 일을 관리하는 사람\n' > PRODUCT.md
cat > docs/features/carry/PRD.md <<'MD'
# carry

## Purpose
못 끝낸 일을 다음 날로 옮긴다.

## Problem
못 끝낸 일을 다음 날 다시 적는다 (가설)

## Solution
미정. 옮길 일을 언제 고르게 할지 시안으로 정해야 함

## Scope
미정

## Success Criteria
미정
MD
printf 'todos = []\n' > app.py
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.sh("git diff --quiet -- app.py").returncode == 0, "조건이 비었는데 구현함"
    assert ctx.sh("git ls-files --others --exclude-standard -- '*.py'").stdout.strip() == "", "조건이 비었는데 코드를 만듦"
    assert re.search(r"시안", ctx.final_text) and re.search(r"범위|Scope", ctx.final_text), "빈칸을 보이지 않음"
