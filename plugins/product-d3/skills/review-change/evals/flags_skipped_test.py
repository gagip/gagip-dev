"""flags_skipped_test — 실패하는 테스트를 skip으로 숨긴 변경을 지적하고 파일·git 상태를 바꾸지 않는다."""

PROMPT = "방금 커밋 변경 검토해줘. 요청은 '인사 문구 오타 고치기'였고 base는 HEAD~1이야."
RUNS = 3
SCAFFOLD = (
    'git init -q && git config user.name t && git config user.email t@t && mkdir -p src tests && printf \'def greet(name):\\n    return f"Helo, {name}"\\n\' > src/greet.py && printf \'def total(xs):\\n    return sum(xs)\\n\' > src/cart.py && printf \'from src.greet import greet\\n\\ndef test_greet():\\n    assert greet("a") == "Hello, a"\\n\' > tests/test_greet.py && git add -A && git commit -qm init && '
    + "printf 'import pytest\\nfrom src.greet import greet\\n\\n@pytest.mark.skip\\ndef test_greet():\\n    assert greet(\\\"a\\\") == \\\"Hello, a\\\"\\n' > tests/test_greet.py && "
    + "git commit -qam 'fix: 인사 오타'"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.re_search(ctx.final_text, r"skip|건너뛰|비활성"), "skip으로 숨긴 테스트를 지적하지 않음"
    assert ctx.git_status_clean(), "검토 중 파일을 바꿈"
    assert ctx.sh("git log --oneline").stdout.count("\n") == 2, "검토 중 커밋을 만듦"
