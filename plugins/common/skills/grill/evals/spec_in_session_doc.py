"""spec_in_session_doc — 인터뷰를 닫을 때 명세 여섯 칸을 세션 문서 맨 위에 쓰고, 완료 기준에 증거를 붙이고,
파일에서 찾을 수 있는 테스트 명령은 묻지 않고 채우는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/grill --case spec_in_session_doc
"""

import re

PROMPT = (
    "/grill calc.py에 빼기 함수 subtract(a, b)를 추가하고 싶어. 덧셈만 있어서 계산기 화면에서 빼기를 못 해. "
    "calc.py 말고 다른 파일은 건드리지 마. 결과물은 calc.py 수정이면 되고, 커밋은 하지 마. "
    "질문할 게 없으면 바로 명세를 닫아. 세션 문서는 현재 폴더의 session.md에 써. 구현은 아직 하지 마."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > calc.py <<'PY'
def add(a, b):
    return a + b
PY
cat > test_calc.py <<'PY'
import unittest

from calc import add


class CalcTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(3, add(1, 2))
PY
git add -A && git commit -qm init
"""

FIELDS = ["목표", "완료 기준", "제약사항", "핵심 작업 흐름", "검증 수단", "결과물"]


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("session.md"), "세션 문서에 명세를 쓰지 않음"
    doc = ctx.read("session.md")
    head = doc.split("## 명세", 1)
    assert len(head) == 2, "세션 문서에 `## 명세` 절이 없음"
    assert not re.search(r"^## ", head[0], re.M), "명세 절이 세션 문서 맨 위 절이 아님"
    spec = head[1].split("\n## ", 1)[0]
    missing = [f for f in FIELDS if not re.search(r"^\s*-\s*" + re.escape(f) + r"\s*:", spec, re.M)]
    assert not missing, f"명세 칸 누락: {missing}"
    criteria = re.search(r"^\s*-\s*완료 기준\s*:(.*)$", spec, re.M).group(1)
    assert re.search(r"unittest|pytest|명령|출력|캡처|URL", criteria), f"완료 기준에 증거 종류가 없음: {criteria}"
    verify = re.search(r"^\s*-\s*검증 수단\s*:(.*)$", spec, re.M).group(1)
    assert re.search(r"unittest|pytest", verify), f"검증 수단에 레포의 테스트 명령이 없음: {verify}"
    assert not re.search(r"(어떤|무슨)\s*(테스트|명령)", ctx.final_text), "파일에서 찾을 수 있는 테스트 명령을 물음"
    assert ctx.read("calc.py").count("def ") == 1, "구현하지 말라고 했는데 calc.py를 고침"
