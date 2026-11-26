"""flags_out_of_scope — 요청과 무관한 파일 변경을 요청에 없는 변경으로 지적한다."""

PROMPT = "방금 커밋 변경 검토해줘. 요청은 'src/greet.py 인사 문구 오타 고치기'였고 base는 HEAD~1이야."
RUNS = 3
SCAFFOLD = (
    'git init -q && git config user.name t && git config user.email t@t && mkdir -p src tests && printf \'def greet(name):\\n    return f"Helo, {name}"\\n\' > src/greet.py && printf \'def total(xs):\\n    return sum(xs)\\n\' > src/cart.py && printf \'from src.greet import greet\\n\\ndef test_greet():\\n    assert greet("a") == "Hello, a"\\n\' > tests/test_greet.py && git add -A && git commit -qm init && '
    + "printf 'def greet(name):\\n    return f\\\"Hello, {name}\\\"\\n' > src/greet.py && "
    + "printf 'def total(xs):\\n    return round(sum(xs) * 1.1)\\n' > src/cart.py && "
    + "git commit -qam 'fix: 인사 오타'"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"cart\.py"), "범위 밖 파일을 짚지 않음"
    assert ctx.re_search(ctx.final_text, r"요청에 없|범위 밖"), "요청에 없는 변경으로 분류하지 않음"
    assert ctx.git_status_clean(), "검토 중 파일을 바꿈"
