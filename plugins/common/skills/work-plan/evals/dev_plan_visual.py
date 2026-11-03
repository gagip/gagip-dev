"""dev_plan_visual — 화면이 바뀌고 고를 선택지가 있는 개발 계획이면 계획서 옆에 계획 시각 자료(HTML 한 장)를
만들어 계획서에서 가리키고, 지금 모습과 바뀐 모습·선택지 비교를 담는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case dev_plan_visual
"""

import re

PROMPT = (
    "home.html 맨 위 날짜 아래에 '지금까지 N일 측정했어요' 한 줄을 넣고 싶어. 측정 실패한 날도 셀지는 정해야 해. "
    "구현 계획서 써줘. 구현은 아직 하지 마. 계획서와 딸린 파일은 모두 docs/ 아래에만 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > home.html <<'HTML'
<!doctype html><html lang="ko"><body>
<header><h1 id="today">12월 17일 목요일</h1></header>
<section class="card"><h2>오늘 결과</h2><p>8개 영역 모두 지난번과 같아요</p></section>
</body></html>
HTML
cat > records.json <<'JSON'
[{"day": "2026-12-15", "status": "SUCCESS"}, {"day": "2026-12-16", "status": "FAILED"}, {"day": "2026-12-17", "status": "SUCCESS"}]
JSON
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    plans = [p for p in ctx.sh("ls docs/*.md docs/**/*.md 2>/dev/null").stdout.split() if p]
    assert plans, "계획서(md)가 docs/ 아래에 없음"
    htmls = [p for p in ctx.sh("find docs -name '*.html'").stdout.split() if p]
    assert htmls, "화면이 바뀌는 계획인데 계획 시각 자료(HTML)가 없음"

    visual = ctx.sh(f"cat {htmls[0]}").stdout
    assert re.search(r"지금|현재|전\s*/\s*후|before", visual, re.I), "지금 모습과의 비교가 없음"
    assert re.search(r"측정했어요", visual), "계획한 문구가 시각 자료에 없음"
    assert re.search(r"권장", visual), "선택지에 권장안 표시가 없음"
    assert re.search(r"실패|FAILED", visual), "측정 실패를 셀지에 대한 선택지 비교가 없음"
    assert re.search(r"dashed", visual) and re.search(r"checkbox", visual, re.I), "새로 생기는 부분 점선 표시와 켜고 끄는 토글이 없음"
    assert re.search(r"하지 않|범위 밖|빼", visual), "이번에 하지 않는 것 칸이 없음"

    plan_text = "\n".join(ctx.sh(f"cat {p}").stdout for p in plans)
    name = htmls[0].split("/")[-1]
    assert name in plan_text, f"계획서가 시각 자료({name})를 가리키지 않음"

    changed = [ln[3:].strip('"') for ln in ctx.sh("git status --porcelain -uall").stdout.splitlines()]
    outside_docs = [p for p in changed if not p.startswith("docs/")]
    assert not outside_docs, f"계획 단계에서 docs/ 밖을 바꿈: {outside_docs}"
