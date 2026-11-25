"""product_spec — 방향 문서가 있는 제품의 신규 기능 계획은 SPEC.md로 쓰고 상태 칸을 남긴다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case product_spec
"""

import re

PROMPT = (
    "오늘 못 끝낸 할 일을 다음 날로 옮기는 기능 계획서 써줘. 신규 기능이야. 묻지 말고 초안부터 쓰고 모르는 건 "
    "비워 둬. 구현은 하지 마."
)
RUNS = 3
# 검수 기준이 다 채운 계획서를 전제해, 빈칸이 정답인 이 케이스에는 LLM 채점을 쓰지 않는다
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p product
cat > product/PRODUCT.md <<'MD'
# 할 일 앱
대상 사용자: 하루 할 일을 혼자 관리하는 사람
핵심 가치: 오늘 할 일을 바로 안다
비목표: 팀 협업과 공유
MD
printf 'todos = []\n' > app.py
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    specs = ctx.sh("find product -name SPEC.md").stdout.split()
    assert len(specs) == 1, f"SPEC.md가 하나가 아님: {specs}"
    doc = ctx.read(specs[0])
    assert re.search(r"상태\W*:\W*(탐색|시안|보류)", doc), "단계 상태가 없거나 시작 조건 전에 개발로 넘김"
    assert re.search(r"크기\W*:\W*신규", doc), "작업 크기가 없음"
    assert "가설" in doc, "근거 없는 문제를 가설로 표시하지 않음"
    assert re.search(r"가정", doc), "위험한 가정이 없음"
    assert ctx.sh("git diff --quiet -- app.py").returncode == 0, "계획 단계에서 코드를 고침"
    plans = ctx.sh("find . -name '*계획*.md'").stdout.split()
    assert not plans, f"계획서를 따로 만듦: {plans}"
