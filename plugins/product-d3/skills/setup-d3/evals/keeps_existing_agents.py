"""keeps_existing_agents — 기존 AGENTS.md가 있으면 덮어쓰지 않고, 승인 전에는 블록을 넣지 않는다."""

PROMPT = "이 레포에 Product D3 적용해줘."
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && printf '# 팀 규칙\\n- 커밋 메시지는 영어로 쓴다.\\n' > AGENTS.md && mkdir -p src && printf 'items = []\n' > src/app.py && "
    "printf '# 장보기 메모\\n혼자 사는 사람용 장보기 목록 앱\\n' > README.md && git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    agents = ctx.read("AGENTS.md")
    assert "커밋 메시지는 영어로 쓴다" in agents, "기존 AGENTS.md 내용을 지움"
    assert "<!-- product-d3 start -->" not in agents, "승인 전에 AGENTS.md에 블록을 넣음"
    assert not ctx.exists("CLAUDE.md"), "CLAUDE.md를 만듦"
