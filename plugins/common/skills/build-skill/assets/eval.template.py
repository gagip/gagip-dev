"""<케이스 이름> — <무엇을 검증하는지 한 줄>.

build-skill 러너용 결정론적 테스트 케이스. 1파일 1케이스.
    python3 <build-skill>/scripts/run_skill_test.py <대상 스킬 경로> --case <이 파일 stem>
"""

# 필수: claude -p에 던질 사용자 프롬프트
PROMPT = "<사용자가 칠 법한 현실적인 프롬프트>"

# 선택: 반복 횟수 (기본 3). 개발 중엔 러너에 --runs 1
RUNS = 3

# 선택: 각 run 전 임시 디렉토리(= claude의 cwd)에서 실행할 bash. 격리 환경 구성.
SCAFFOLD = r"""
set -e
# 예: git 저장소 + 변경사항
# git init -q && git config user.email e@e.com && git config user.name E
# printf 'x\n' > file.txt
"""

# 선택: 권한 모드 (기본 bypassPermissions — 격리된 임시 디렉토리라 안전)
# PERMISSION_MODE = "bypassPermissions"


def check(ctx):
    """결과 검증. 전부 코드 — LLM 심판 없음. AssertionError 메시지가 실패 사유로 뜬다.

    정확한 문자열보다 안정적 결과로 검증한다 (Claude 행동이 비결정적).
    ctx 헬퍼: skill_fired / tool_used / bash_ran / bash_order / sh / git_log_subject /
             git_status_clean / read / exists / final_text / re_match / re_search
    """
    assert ctx.skill_fired(), f"스킬 미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"

    # 예시:
    # assert ctx.re_match(ctx.git_log_subject(), r"^(feat|fix|chore): .+")
    # assert ctx.bash_order(r"git\s+add", r"git\s+commit")
    # assert not ctx.bash_ran(r"git\s+push")
    # assert ctx.exists("*.md")
    # assert "기대 문구" in ctx.read("output/*.txt")
