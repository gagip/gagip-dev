"""fires_on_inline_code — 파일 없이 답변에 넣을 짧은 함수 작성 요청에도 deliver-work가 열린다."""

PROMPT = "리스트에서 순서를 지키며 중복을 없애는 파이썬 함수 하나 짜줘."
RUNS = 3
# 7단계 흐름을 따라야 하는 스킬이라 haiku는 대상이 아니다 (모델 매트릭스에서 제외)
MODELS = ["sonnet", "opus"]
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
