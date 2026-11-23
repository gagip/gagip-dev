"""prd_new_feature — 만드는 내내 볼 기획서 요청을 착수 합의용 계획서와 구분해 이 스킬로 쓰고, 구현 방식을 넣지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/write-docs --case prd_new_feature
"""

PROMPT = (
    "측정 결과를 가족에게 링크로 공유하는 기능의 PRD 작성해줘. 디자이너와 개발자가 만드는 내내 기준으로 볼 문서야. "
    "목표는 가족이 앱 없이 결과를 보는 거야. 묻지 말고 초안부터 써. 모르는 건 확인 필요로 남겨. "
    "docs/PRD-결과공유.md에 저장하고 작업 자료는 work/ 폴더에 둬."
)

RUNS = 3
GRADER = "llm"
REVIEW_FOCUS = "구현 방식 없이 목표·사용자·확인 방법만으로 문서가 서는가"

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p src
cat > src/report.py <<'PY'
def build_report(result):
    return {"score": result.score, "measured_at": result.measured_at}
PY
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/PRD-결과공유.md"), "문서가 생성되지 않음"
    doc = ctx.read("docs/PRD-결과공유.md")

    assert ctx.files_read(r"기획-계획서\.md") or ctx.bash_ran(r"기획-계획서\.md"), "기획 계획서 가이드라인을 열지 않음"
    for section in ["배경", "성공 기준", "범위", "요구사항", "제약", "확인 필요"]:
        assert section in doc, f"절 누락: {section}"

    head, _, _ = doc.partition("개발 참고")
    assert not ctx.re_search(head, r"\.py\b|build_report|REST|엔드포인트|테이블 설계"), "본문에 구현 내용이 들어감"
    assert [p for p in ctx.sh("ls work").stdout.split() if "사실표" in p], "사실표가 work/에 없음"
