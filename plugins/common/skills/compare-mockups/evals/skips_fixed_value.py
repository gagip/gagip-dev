"""skips_fixed_value — 바꿀 값이 정해진 화면 수정에는 시안을 만들지 않는다."""

PROMPT = "home.html의 버튼 문구를 저장에서 저장하기로 바꿔줘. 커밋은 하지 마."
RUNS = 3
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && "
    "printf '<!doctype html><meta charset=\"utf-8\"><button>저장</button>\\n' > home.html && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert not ctx.skill_fired(), f"값이 정해진 수정에 발동: {ctx.skill_invocations()}"
    assert len(ctx.sh("find . -name '*.html'").stdout.split()) == 1, "시안 파일을 만듦"
