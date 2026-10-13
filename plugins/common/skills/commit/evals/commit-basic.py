"""commit 스킬 기본 동작 — build-skill 러너용 결정론적 테스트.

스테이징되지 않은 변경사항(수정 1 + 신규 1)이 있는 임시 저장소에서 "커밋해줘" 했을 때:
- git add -A 가 커밋 전에 실행되고
- 커밋 메시지가 <type>: <요약> 형식이며
- git push 는 실행되지 않고
- 스킬이 실제로 발동한다.
"""

PROMPT = "커밋해줘"
RUNS = 3

SCAFFOLD = r"""
set -e
git init -q
git config user.email eval@example.com
git config user.name "Eval Bot"
printf 'console.log("hello");\n' > app.js
git add app.js
git commit -q -m "chore: 초기 스캐폴드 커밋"
printf 'console.log("hello world");\n' > app.js
printf '# Notes\n\nscratch notes\n' > NOTES.md
"""

_TYPES = r"feat|fix|refactor|style|test|docs|chore|ai"


def check(ctx):
    # 스킬이 발동했다
    assert ctx.skill_fired(), (
        f"commit 스킬 미발동. Skill 호출: {ctx.skill_invocations()} / 전체 툴: {ctx.tool_names()}"
    )

    # 새 커밋이 생겼다 (스캐폴드 커밋 위에 1개 더)
    count = ctx.run(["git", "rev-list", "--count", "HEAD"]).stdout.strip()
    assert count == "2", f"커밋 수가 2가 아님: {count}"

    # 커밋 메시지 형식
    subject = ctx.git_log_subject()
    assert ctx.re_match(subject, rf"^({_TYPES}): .+"), f"메시지 형식 위반: {subject!r}"

    # 두 변경(app.js 수정, NOTES.md 신규)이 모두 커밋에 들어갔다 → 작업트리 깨끗
    assert ctx.git_status_clean(), (
        f"작업트리가 안 깨끗함: {ctx.run(['git','status','--porcelain']).stdout!r}"
    )
    committed = ctx.run(["git", "show", "--name-only", "--format=", "HEAD"]).stdout
    assert "app.js" in committed and "NOTES.md" in committed, f"커밋 파일: {committed!r}"

    # add 가 commit 보다 먼저
    assert ctx.bash_order(r"git\s+add", r"git\s+commit"), (
        f"git add → git commit 순서 아님. bash: {ctx.bash_cmds}"
    )

    # push 안 함
    assert not ctx.bash_ran(r"git\s+push"), f"git push 실행됨. bash: {ctx.bash_cmds}"
