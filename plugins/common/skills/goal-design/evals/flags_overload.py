"""flags_overload — 사람이 정할 일이 많은 목표를 하루에 몰아넣으면 기한 판정에서 들어가지 않는다고 밝히고 축소안을 내는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/goal-design --case flags_overload
"""

import re
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_design.py"

PROMPT = (
    "내일 하루 안에 끝낼 목표들을 설계해줘. 신규 서비스의 타겟 고객 정의, 가격 정책 결정, "
    "랜딩 페이지 문구 확정, 투자자 발표 자료 완성. 넷 다 내가 직접 정하고 검토해야 하는 일이고, "
    "내일 오후 2시부터 5시까지는 회의가 있어. 자료 조사나 초안은 에이전트가 해도 돼. "
    "docs/goals.md에 저장해줘."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p docs
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/goals.md"), "설계 문서가 생성되지 않음"
    doc = ctx.read("docs/goals.md")

    assert "기한" in doc, "기한 판정 절 누락"
    assert re.search(r"안 들어감|빠듯함", doc), "과부하인데 기한 판정이 모두 '들어감'"
    assert re.search(r"축소|제외|미루|옮기", doc), "들어가지 않는데 축소안이 없음"

    result = ctx.sh([sys.executable, str(CHECK_SCRIPT), "docs/goals.md"])
    assert result.returncode == 0, f"check_design 오류:\n{result.stdout[-800:]}"
