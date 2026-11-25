"""product_result — 결과를 보고 유지할지 정하는 요청에 열리고 자료가 모자라면 판단 유보를 권한다."""

import re

PROMPT = "product/features/reminder/SPEC.md 기능 결과 보고 유지할지 정하자. 측정값은 data.csv에 있어."
RUNS = 3
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p product/features/reminder
echo '# 할 일 앱' > product/PRODUCT.md
cat > product/features/reminder/SPEC.md <<'MD'
상태: 결과 확인
크기: 신규
볼 값: 알림을 받은 사람이 당일 할 일을 하나 이상 끝낸 비율
유지 기준: 30명 이상에서 40% 이상
다시 볼 날짜: 쓰기 시작한 날에서 14일 뒤
MD
printf 'user,done\n1,1\n2,1\n3,0\n4,1\n' > data.csv
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert re.search(r"판단 유보", ctx.final_text), "표본이 모자란데 판단 유보를 권하지 않음"
    assert not re.search(r"유지를 권|유보하지 않", ctx.final_text), "표본이 모자란데 유지를 권함"
    assert ctx.git_status_clean(), "정하기 전에 파일을 고침"
