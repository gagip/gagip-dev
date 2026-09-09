"""scaffolds_narrow_server — 이 스킬의 규약대로 서버·설치·테스트 세 파일이 생기고 stdio 로 답한다.

**이 케이스가 재는 것은 규약 준수이지 서버 품질이 아니다.** 스킬 없이 만들어도 좁은 도구와
입력 검증은 잘 나온다(실측: 공식 SDK 기반 Node 서버 + enum 화이트리스트). 여기서 보는 것은
의존성 없이 어느 하네스에서나 그대로 도는 배치를 따르는가다 — 표준 라이브러리만 쓰는 파이썬
파일 셋. baseline 이 떨어져도 "스킬이 더 안전한 서버를 만든다"로 읽지 않는다.

서버 파일 여러 개를 만드는 케이스라 러너 기본 제한시간(300초)으로는 빠듯하다.
`--timeout 600` 으로 돌린다.
"""

PROMPT = (
    "사내 상태 API(https://api.example.com/v1)를 붙이는 MCP 서버를 만들어줘. "
    "읽기 전용이고, 'deploy' 와 'health' 두 항목만 볼 수 있으면 돼. "
    "다른 항목은 못 보게 막아줘. 서버는 ./statusmcp 폴더에 만들고, "
    "네가 실제 API 를 부를 수는 없으니 등록은 하지 말고 파일만 만들어줘."
)
RUNS = 2


def check(ctx):
    # 실질 검사를 먼저 둔다 — 발동 여부를 앞에 두면 baseline(스킬 없이 실행)이 첫 줄에서
    # 멈춰 버려, 스킬이 실제로 무엇을 더 해내는지 대조가 안 된다.
    assert ctx.exists("statusmcp/server.py"), "server.py 없음"
    assert ctx.exists("statusmcp/setup.py"), "setup.py 없음"
    assert ctx.exists("statusmcp/test_*.py"), "게이트 테스트 파일 없음"

    # 서버가 MCP stdio 로 실제로 답하는지 — 파일만 있고 안 도는 경우를 거른다.
    handshake = (
        '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
        '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
    )
    out = ctx.sh(f"printf '%s' '{handshake}' | python3 statusmcp/server.py").stdout
    assert ctx.re_search(out, r'"serverInfo"'), f"initialize 응답 없음: {out[:300]}"
    assert ctx.re_search(out, r'"tools"'), f"tools/list 응답 없음: {out[:300]}"

    # 좁히기가 목적이므로 범용 통로가 있으면 안 된다.
    server = ctx.read("statusmcp/server.py")
    assert not ctx.re_search(server, r'"name":\s*"(call_api|request|raw_.*|api_call)"'), \
        "범용 API 통로 도구가 노출됨"

    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
