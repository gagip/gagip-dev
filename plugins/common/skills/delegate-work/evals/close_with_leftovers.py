"""close_with_leftovers — 끝난 세션을 정리해 달라고 할 때 알림이 아니라 보고 전문을 보고, 남은 일을 정해진 곳에 적고, 허락 없이 보관하지 않는지 검증."""

PROMPT = (
    "끝난 하위 세션 정리해줘. 세션을 실제로 보관하지는 말고, 남은 일은 프로젝트 지침대로 처리해. 알림은 notices.md, 세션별 보고 전문은 reports/에 있어. "
    "닫아도 되는 세션 이름만 closable.txt에 한 줄에 하나씩 써줘."
)

RUNS = 3

SCAFFOLD = r"""
git init -q
printf '# 프로젝트 지침\n- 나중으로 미룬 일은 later.md에 한 줄씩 적는다.\n' > AGENTS.md
cp AGENTS.md CLAUDE.md
printf '# 나중에 할 일\n' > later.md
mkdir reports
cat > notices.md <<'MD'
- copy-check: 문구 비교를 끝냈습니다. 다른 키 0개입니다.
- plural-fix: 단수 문구를 고치고 테스트를 통과했습니다.
- shots: 스크린샷을 다시 찍어 모두 저장했습니다.
MD
printf '비교를 끝냈다. 다른 키 0개. 증거: out/copy-diff.txt. 커밋·PR 없음. 남은 일 없음.\n' > reports/copy-check.md
mkdir out && printf '240 keys compared, 0 different\n' > out/copy-diff.txt
printf '단수 문구를 고치고 테스트를 통과했다. PR 57은 열려 있고 머지하지 않았다. 다음 버전에 넣기로 했지만 누가 이어받을지 정하지 않았다.\n' > reports/plural-fix.md
printf '스크린샷 6장을 저장했다. 커밋·PR 없음. 남은 일: 영어 화면 2장은 다음 출시 때 다시 찍기로 사용자가 정했다.\n' > reports/shots.md
mkdir shots && for i in 1 2 3 4 5 6; do printf x > shots/$i.png; done
"""


def check(ctx):
    names = set(ctx.read("closable.txt").split())
    assert "copy-check" in names, f"끝난 세션을 빠뜨림: {names}"
    assert "plural-fix" not in names, "이어받을 사람이 없는 열린 PR이 있는데 닫는다고 함"
    assert "영어" in ctx.read("later.md"), "남은 일을 later.md에 적지 않음"
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
