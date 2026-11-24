"""choose_executor — 결과를 바로 쓸 독립 검토는 서브에이전트, 대화가 필요한 일과 별도 PR은 하위 세션, 파일 하나 확인은 직접으로 고르는지 검증."""

import json

PROMPT = (
    "지금부터 네가 지휘 세션이야. 아래 네 가지를 하위 세션으로 돌릴지, 서브에이전트로 할지, 네가 직접 할지 나눠줘. "
    "아직 실행하지 말고 현재 폴더의 split.json에 {\"a\":\"session|subagent|direct\", ...}로만 써.\n"
    "a. 네가 방금 쓴 조사 보고서 30쪽을 맥락 없는 눈으로 검토하기. 지적을 받아서 네가 바로 보고서를 고쳐야 해.\n"
    "b. 설정 화면 새 구성을 시안 보면서 나랑 하나씩 정하기\n"
    "c. 다른 레포의 로그인 버그를 고쳐 PR 내기\n"
    "d. package.json의 버전이 1.2.1인지 보기"
)

RUNS = 3

SCAFFOLD = "git init -q && printf '{\"version\":\"1.2.1\"}\\n' > package.json"


def check(ctx):
    assert ctx.exists("split.json"), "split.json 없음"
    got = json.loads(ctx.read("split.json"))
    want = {"a": "subagent", "b": "session", "c": "session", "d": "direct"}
    assert got == want, f"고르기 다름: {got}"
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
