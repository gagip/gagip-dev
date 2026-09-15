"""blocks_without_brief — 기획서 없이 시안부터 요청하면 곧바로 시안 생성으로 새지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/mockup-review --case blocks_without_brief
"""

PROMPT = "알림 설정 화면 디자인 시안 3개 뽑아줘."

RUNS = 3

# 기획서 파일이 전혀 없는 빈 디렉토리 — 전제조건 확인 없이 바로 시안 생성으로
# 새면 안 된다.


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"

    mockup_files = [
        p for p in ctx.workdir.rglob("*")
        if p.is_file() and p.suffix in (".html", ".htm")
    ]
    assert not mockup_files, f"기획서 없이 시안 파일부터 생성함: {mockup_files}"

    assert ctx.re_search(ctx.final_text, r"(타겟|문제|목적|기획서|screen-brief)"), (
        f"기획서/타겟/문제/목적 확인 없이 진행함: {ctx.final_text!r}"
    )
