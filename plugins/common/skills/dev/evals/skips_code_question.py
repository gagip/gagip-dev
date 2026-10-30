"""skips_code_question — 고칠 거리를 묻기만 하는 질문에는 dev가 열리지 않는다."""

PROMPT = "greet.py에 오타 있어?"
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && "
    "printf 'def greet(name):\\n    return f\"Helo, {name}\"\\n' > greet.py && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert not ctx.skill_fired(), f"질문인데 발동: {ctx.skill_invocations()}"
