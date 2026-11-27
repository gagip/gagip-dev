"""fires_on_oneoff_script — 제품 코드가 아닌 일회성 스크립트 작성 요청에도 deliver-work가 열린다."""

PROMPT = "sales.csv의 amount 열 합계를 출력하는 파이썬 스크립트 짜줘. 커밋은 하지 마."
RUNS = 3
# 7단계 흐름을 따라야 하는 스킬이라 haiku는 대상이 아니다 (모델 매트릭스에서 제외)
MODELS = ["sonnet", "opus"]
SCAFFOLD = (
    "git init -q && git config user.name t && git config user.email t@t && "
    "printf 'item,amount\\napple,3\\npear,4\\n' > sales.csv && "
    "git add -A && git commit -qm init"
)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
