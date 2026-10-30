"""fires_on_small_fix — 계획서 없는 작은 수정 요청에도 dev가 열린다."""

PROMPT = "greet.py에서 인사 문구 오타 고쳐줄래?"
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && "
    "printf 'def greet(name):\\n    return f\"Helo, {name}\"\\n' > greet.py && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
