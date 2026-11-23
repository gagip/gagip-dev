"""feature_spec_stale_memo — 옛 메모와 코드가 다르면 코드를 따르고, 코드로 알 수 없는 사실은 단정하지 않으며,
사실표는 문서와 분리하고, 본문에 코드 이름을 넣지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/write-docs --case feature_spec_stale_memo
"""

import re

PROMPT = (
    "이 앱의 측정 알림 기능 명세 써줘. 기획자랑 디자이너가 계속 기준으로 볼 문서야. "
    "참고로 notes/옛-기획메모.md에 정리해 둔 게 있어. docs/기능명세-측정알림.md에 저장하고 "
    "작업 자료는 work/ 폴더에 둬. 게시는 하지 마."
)

RUNS = 3
GRADER = "llm"
REVIEW_FOCUS = "옛 메모와 코드가 다를 때 코드 기준으로 썼고 그 차이를 확인 필요로 남겼는가"

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
mkdir -p src notes
cat > src/alarm.py <<'PY'
DEFAULT_TIME = "20:00"
REPEAT_OPTIONS = ["매일", "평일", "직접 고르기"]


def save_alarm(api, alarm):
    try:
        api.put("/alarm", alarm)
    except ConnectionError:
        return "저장하지 못했어요. 다시 시도해 주세요."
    return None


def push_title(kind):
    return "측정할 시간이에요" if kind == "alarm" else None
PY
cat > notes/옛-기획메모.md <<'MD'
# 측정 알림 메모
- 기본 시각은 오전 09:00
- 운영 서버에서 푸시를 하루 최대 3회로 제한함
MD
git add -A && git commit -qm init
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.exists("docs/기능명세-측정알림.md"), "문서가 생성되지 않음"
    doc = ctx.read("docs/기능명세-측정알림.md")

    assert ctx.files_read(r"기능-명세\.md") or ctx.bash_ran(r"기능-명세\.md"), "기능 명세 가이드라인을 열지 않음"
    for section in ["기획 의도", "화면 규칙", "예외 처리", "범위 외", "확인 필요"]:
        assert section in doc, f"절 누락: {section}"

    head, _, _ = doc.partition("개발 참고")
    assert "20:00" in head or "오후 8" in head, "코드의 기본 시각을 본문에 쓰지 않음"
    assert not ctx.re_search(head, r"\.py\b|DEFAULT_TIME|save_alarm"), "본문에 코드 이름이 들어감"

    heading = re.search(r"^#+.*확인 필요", doc, re.M)
    assert heading, "확인 필요 절 제목이 없음"
    body, needs_check = doc[:heading.start()], doc[heading.start():]
    assert not ctx.re_search(body, r"09:00|오전 9|최대 3회|하루 3회"), "옛 메모 값이 본문에 들어감"
    assert ctx.re_search(needs_check, r"3회|횟수 제한"), "코드로 확인 못 한 푸시 제한이 확인 필요에 없음"

    tables = [p for p in ctx.sh("ls work").stdout.split() if "사실표" in p]
    assert tables, "사실표가 work/에 없음"
    table = ctx.read(f"work/{tables[0]}")
    assert "미확인" in table and "출처" in table, "사실표 형식이 아님"
    assert not re.search(r"사실표", head), "문서 본문에 사실표가 언급됨"

    assert ctx.bash_ran(r"check_doc\.py"), "게시 전 검사를 실행하지 않음"
    assert not ctx.tool_used("mcp__notion"), "게시함"
