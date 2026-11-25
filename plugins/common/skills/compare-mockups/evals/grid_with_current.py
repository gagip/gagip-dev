"""grid_with_current — 자연어 시안 요청에 열리고 현재 화면을 포함한 비교 화면을 만들며 원본을 고치지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/compare-mockups --case grid_with_current
"""

import re

PROMPT = (
    "home.html 첫 화면에서 오늘 할 일과 이번 주 완료 수 중 무엇을 먼저 보여 줄지 시안 만들어줘. 안 두 개면 되고 "
    "배치 순서만 달라야 해. 범위는 이 화면 배치까지야. 묻지 말고 현재 폴더 아래 mockups/에만 저장해. home.html은 고치지 마."
)

RUNS = 3
GRADER = "llm"
REVIEW_FOCUS = "배치 순서만 다르고 없는 기능을 더하지 않았는가"

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > home.html <<'HTML'
<!doctype html><html lang="ko"><meta charset="utf-8"><title>할 일</title>
<style>:root{--main:#2457a6;--bg:#fff}body{font:16px sans-serif;background:var(--bg);width:375px}</style>
<body><h1>할 일</h1><section id="today"><h2>오늘</h2><p>장보기</p><p>책 반납</p></section>
<section id="week"><h2>이번 주</h2><p>완료 4개</p></section></body></html>
HTML
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    files = [p for p in ctx.sh("find mockups -name '*.html'").stdout.split() if not p.endswith("/index.html")]
    assert ctx.exists("mockups/index.html"), "비교 화면 index.html이 없음"
    assert len(files) >= 2, f"안 파일이 둘보다 적음: {files}"
    hub = ctx.read("mockups/index.html")
    assert re.search(r"현재|지금", hub), "비교 화면에 현재 화면이 없음"
    assert not re.search(r"role=[\"']tab", hub), "안을 탭으로 숨김"
    assert ctx.tool_used("Agent") or ctx.tool_used("Task") or "독립 비평 미실행" in ctx.final_text, (
        "독립 비평을 돌리지도 미실행을 밝히지도 않음"
    )
    assert ctx.sh("git diff --quiet -- home.html").returncode == 0, "원본 화면을 고침"
    outside = [
        line[3:]
        for line in ctx.sh("git status --porcelain -uall").stdout.splitlines()
        if not line[3:].strip('"').startswith("mockups/")
    ]
    assert not outside, f"mockups/ 밖에 파일을 만듦: {outside}"
