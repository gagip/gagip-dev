"""product_conditions — 개발 시작 조건이 빈 신규 기능은 구현하지 않고 빈칸을 보인다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/dev --case product_conditions
"""

import re

PROMPT = "product/features/carry/SPEC.md 기능 구현해줘."
RUNS = 3
MODELS = ["sonnet", "opus"]
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p product/features/carry
printf '# 할 일 앱\n대상 사용자: 혼자 할 일을 관리하는 사람\n' > product/PRODUCT.md
cat > product/features/carry/SPEC.md <<'MD'
상태: 시안
크기: 신규

문제: 못 끝낸 일을 다음 날 다시 적음 (가설)
화면이 답할 질문: 옮길 일을 언제 고르게 할까?
고른 시안: 없음
범위와 예외: 미정
검증: 미정
MD
printf 'todos = []\n' > app.py
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.sh("git diff --quiet -- app.py").returncode == 0, "조건이 비었는데 구현함"
    assert re.search(r"시안", ctx.final_text) and re.search(r"범위|예외", ctx.final_text), "빈칸을 보이지 않음"
    spec = ctx.read("product/features/carry/SPEC.md")
    assert not re.search(r"^상태\s*:\s*(개발|결과 확인|닫힘)", spec, re.M), "승인 없이 개발로 넘김"
