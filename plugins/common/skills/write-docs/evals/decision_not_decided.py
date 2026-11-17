"""decision_not_decided — 사용자가 아직 안 정한 결정을 확정으로 쓰지 않고, 현재 유지를 포함한 선택지와 권장안을 쓰는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/write-docs --case decision_not_decided
"""

PROMPT = (
    "결제 알림을 메일에서 문자로 바꿀지 결정 문서 만들어줘. 아직 안 정했고 다음 주 회의에서 대표가 볼 거야. "
    "지금 구조는 src/notify.py에 있어. docs/결정-결제알림.md에 저장하고 작업 자료는 work/ 폴더에 둬."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p src
cat > src/notify.py <<'PY'
def notify_payment(mailer, user, amount):
    mailer.send(user.email, f"{amount}원 결제 완료")
PY
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/결정-결제알림.md"), "문서가 생성되지 않음"
    doc = ctx.read("docs/결정-결제알림.md")

    assert ctx.files_read(r"결정-문서\.md") or ctx.bash_ran(r"결정-문서\.md"), "결정 문서 가이드라인을 열지 않음"
    head = "\n".join(doc.splitlines()[:5])
    assert ctx.re_search(head, r"상태\W{0,6}결정 전"), "제목 바로 아래 상태가 결정 전이 아님"
    assert [p for p in ctx.sh("ls work").stdout.split() if "사실표" in p], "사실표가 work/에 없음"
    assert "권장" in doc, "권장안이 없음"
    assert not ctx.re_search(doc, r"상태\W{0,6}결정됨|확정(했|함|됨)"), "안 정한 결정을 확정으로 씀"
    assert ctx.re_search(doc, r"현재 유지|메일 유지|그대로 유지"), "현재 유지 선택지가 없음"
    assert ctx.re_search(doc, r"다시 볼 조건"), "다시 볼 조건이 없음"
