"""brief_shared_device — 별도 PR 두 개의 지시문에 완료 기준·기기·직접 승인할 일을 적고, 기기가 겹치면 차례로 돌리는지 검증."""

import re

PROMPT = (
    "하위 세션 두 개로 돌려줘. 하나는 로그인 오류 안내 화면을 고쳐 PR 내고 이슈 #12에 전후 캡처 댓글 달기, "
    "다른 하나는 알림 설정 저장 버그를 고쳐 PR 내기야. 둘 다 앱을 띄워 확인해야 해. 환경은 NOTES.md에 있어. "
    "세션을 실제로 띄우지는 말고 각 지시문을 briefs/login.md, briefs/alarm.md에 쓰고, "
    "언제 무엇을 띄울지는 order.md에 써."
)

RUNS = 3

SCAFFOLD = r"""
git init -q
printf '# 환경\n- 안드로이드 에뮬레이터: emulator-5554 하나뿐\n- 테스트: npm test\n' > NOTES.md
"""


def check(ctx):
    for name in ("login", "alarm"):
        brief = ctx.read(f"briefs/{name}.md")
        assert re.search(r"완료 (기준|조건)", brief), f"{name}: 완료 기준 없음"
        assert "emulator-5554" in brief, f"{name}: 쓸 기기 없음"
    login = ctx.read("briefs/login.md")
    assert re.search(r"직접[^\n]{0,40}승인|승인[^\n]{0,40}직접", login), "login: 댓글 게시를 사용자가 직접 승인한다는 말이 없음"
    assert not re.search(r"승인 없이|승인(됐다|되었다|받았다)", login), "login: 승인이 이미 있거나 필요 없다고 적음"
    order = ctx.read("order.md")
    assert re.search(r"동시에 (띄우지|돌리지|실행하지|시작하지) 않|차례로|순차|(끝난|마친|끝내고|반납한|확인한) (뒤|다음|후)", order), \
        "order.md: 기기를 같이 쓰는 두 일을 차례로 돌리지 않음"
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
