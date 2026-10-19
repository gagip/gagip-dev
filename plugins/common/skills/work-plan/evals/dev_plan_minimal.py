"""dev_plan_minimal — 파일 하나를 고치는 개발 작업이면 계획서 한 장을 공통 절로 쓰고, 코드는 건드리지 않으며,
조건(파일 10개 초과·되돌리기 비쌈·연구 판정선)에 들지 않으니 plan-reviewer를 부르지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/work-plan --case dev_plan_minimal
"""

import re

PROMPT = (
    "settings.py의 save_settings가 저장 버튼을 빠르게 두 번 누르면 두 번 저장돼. 한 번만 저장되게 고치는 작업 "
    "계획서 써줘. 구현은 아직 하지 마. docs/계획.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > settings.py <<'PY'
saved = []


def save_settings(values: dict) -> None:
    saved.append(dict(values))
PY
cat > test_settings.py <<'PY'
from settings import save_settings, saved


def test_save_once():
    saved.clear()
    save_settings({"theme": "dark"})
    assert len(saved) == 1
PY
git add -A && git commit -qm init
"""

SECTIONS = ["목표와 완료 기준", "지금 사실", "할 일", "확인 방법", "착수 전 합의", "멈춤 전제", "변경·결정 로그"]


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/계획.md"), "계획서가 생성되지 않음"
    doc = ctx.read("docs/계획.md")

    missing = [s for s in SECTIONS if not re.search(r"^#*\s*" + re.escape(s), doc, re.M)]
    assert not missing, f"공통 절 누락: {missing}"
    assert re.search(r"상태\s*:\s*초안", doc), "승인 전인데 상태가 초안이 아님"
    assert re.search(r"브랜치\s*:", doc), "개발 계획서인데 브랜치명이 없음"
    assert not re.search(r"\bKR\d|\bO\d\.\d|\bD\d\b|사람\((설계|결정|리뷰|실물)\)", doc), "옛 형식(KR·결정 번호·담당 표시)이 남음"
    assert len(doc) < 6000, f"계획서가 너무 김: {len(doc)}자"

    changed = [ln[3:] for ln in ctx.sh("git status --porcelain -uall").stdout.splitlines()]
    outside_docs = [p for p in changed if not p.strip('"').startswith("docs/")]
    assert not outside_docs, f"계획 단계에서 docs/ 밖을 바꿈: {outside_docs}"
    assert not ctx.tool_used("Agent", subagent_type="plan-reviewer"), "검수 조건에 들지 않는데 plan-reviewer를 부름"
