"""single_goal_no_deadline — 기준 없이 목표 하나만 주면 세부 목표로 쪼개고, 사용자가 주지 않은 판정 기준은 후보로 표시하고, 기한이 없으니 일정표를 만들지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/goal-design --case single_goal_no_deadline
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_design.py"
NUMERIC = re.compile(r"\d+(\.\d+)?\s*(%|퍼센트|명|건|개|회|배)")

PROMPT = (
    "신규 가입자가 첫 주 안에 앱을 떠나는 걸 줄이고 싶어. 이 목표를 설계해줘. "
    "기한은 아직 없어. docs/goals.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/goals.md"), "설계 문서가 생성되지 않음"
    doc = ctx.read("docs/goals.md")

    sub_goals = set(re.findall(r"O\d+\.\d+", doc))
    assert len(sub_goals) >= 2, f"세부 목표가 2개 미만: {sorted(sub_goals)}"
    assert re.search(r"KR\d", doc), "KR이 없음"
    assert "후보" in doc, "사용자가 기준을 주지 않았는데 후보 표시가 없음 — 설계를 지어냈을 가능성"

    date_rows = re.findall(r"^\|\s*\d{1,2}/\d{1,2}", doc, re.M)
    assert not date_rows, f"기한이 없는데 날짜표가 있음: {date_rows[:3]}"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/goals.md"])
    assert result.returncode == 0, f"check_design 오류:\n{result.stdout[-800:]}"

    # 요청에 수치가 하나도 없다 — KR의 수치는 전부 칸마다 후보여야 한다
    kr_rows = [l for l in doc.splitlines() if re.match(r"^\|\s*O[\d.]+\s*\|\s*KR\d+", l)]
    invented = [l for l in kr_rows if NUMERIC.search(l.split("|")[3]) and "후보" not in l.split("|")[3]]
    assert not invented, f"요청에 없는 수치를 후보 표시 없이 KR에 씀: {[r.strip()[:70] for r in invented[:3]]}"
