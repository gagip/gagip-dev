"""product_direction_doc — 제품 방향 문서 요청에 열리고 갈리는 자료를 미합의로 남긴다.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/write-docs --case product_direction_doc
"""

import re

PROMPT = (
    "notes 폴더 자료로 제품 방향 문서로 정리해줘. 새 기능을 할지 정할 때 팀이 계속 볼 거야. 묻지 말고 초안부터 써. "
    "product/PRODUCT.md에 저장하고 작업 자료는 work/ 폴더에 둬."
)
RUNS = 3
GRADER = "llm"
REVIEW_FOCUS = "갈리는 방향을 하나로 합치거나 없는 비목표를 확정하지 않았는가"
SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p notes
cat > notes/정하는사람.md <<'MD'
날짜: 2026-03-02, 말한 사람: 제품 책임자
대상은 혼자 할 일을 관리하는 사람으로 정했다. 팀 협업은 하지 않는다.
MD
cat > notes/회의.md <<'MD'
날짜: 2026-03-10
첫 화면은 오늘 할 일이 중심이라는 쪽과 한 달 흐름이 중심이라는 쪽이 갈렸다. 정하지 않았다.
MD
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.files_read(r"제품-방향\.md") or ctx.bash_ran(r"제품-방향\.md"), "제품 방향 가이드를 열지 않음"
    doc = ctx.read("product/PRODUCT.md")
    for word in ["대상 사용자", "비목표", "성공 기준", "미합의", "확정"]:
        assert word in doc, f"누락: {word}"
    open_items = re.search(r"^#+[^\n]*미합의[^\n]*\n(.*?)(?=^## |\Z)", doc, re.M | re.S)
    assert open_items, "미합의 절이 없음"
    assert "오늘" in open_items.group(1) and "한 달" in open_items.group(1), "갈린 두 방향이 미합의 절에 없음"
