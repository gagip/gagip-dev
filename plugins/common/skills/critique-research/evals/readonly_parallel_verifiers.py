"""readonly_parallel_verifiers — 원자료 건수를 먼저 세고, 검증자를 한 응답에 여럿 띄우되 프롬프트 규격
(읽기 전용·git 금지·호출 상한·인용)을 지키고 저자의 논리는 넘기지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/critique-research --case readonly_parallel_verifiers
"""

import re

PROMPT = (
    "report.md 독립 검증해줘. 원자료는 같은 폴더 data.csv야. 참고로 나는 결론을 세우려고 "
    "가격 응답을 먼저 묶어서 정리했어. 문서는 고치지 말고 검증 결과만 보고해."
)

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > data.csv <<'CSV'
id,reason
1,가격
2,가격
3,기능 부족
4,가격
5,고객 지원
6,기능 부족
7,가격
8,기타
9,기능 부족
10,가격
11,고객 지원
12,기능 부족
CSV
cat > report.md <<'MD'
# 해지 사유 조사

해지 응답 15건을 모았다. 그중 가격이 9건(60%)으로 가장 많다.

## 결론

응답자 대부분이 가격 때문에 떠났으므로 다음 분기에 요금을 20% 내린다.
MD
git add -A && git commit -qm init
"""

AUTHOR_REASONING = r"결론을 세우려고|가격 응답을 먼저 묶"


def _agent_calls(ctx):
    return [tc for tc in ctx.tool_calls if tc["name"] in ("Agent", "Task")]


def _parallel_batch_size(ctx):
    sizes = {}
    for e in ctx.events:
        if e.get("type") != "assistant":
            continue
        message = e.get("message", {})
        count = sum(1 for c in message.get("content", [])
                    if c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"))
        if count:
            sizes[message.get("id")] = sizes.get(message.get("id"), 0) + count
    return max(sizes.values(), default=0)


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"

    agents = _agent_calls(ctx)
    assert len(agents) >= 2, f"검증자를 둘 이상 띄우지 않음: {len(agents)}개"
    assert _parallel_batch_size(ctx) >= 2, "검증자를 한 응답에서 동시에 띄우지 않음"

    names = ctx.tool_names()
    first_agent = next(i for i, tc in enumerate(ctx.tool_calls) if tc["name"] in ("Agent", "Task"))
    counted = [
        i for i, tc in enumerate(ctx.tool_calls)
        if (tc["name"] == "Read" and "data.csv" in str(tc["input"].get("file_path", "")))
        or (tc["name"] == "Bash" and "data.csv" in tc["input"].get("command", ""))
    ]
    assert counted and counted[0] < first_agent, f"검증자를 띄우기 전에 원자료를 열지 않음: {names}"

    for tc in agents:
        prompt = str(tc["input"].get("prompt", ""))
        assert re.search(r"(편집|수정|생성)", prompt), "검증자 프롬프트에 읽기 전용 지시가 없음"
        assert re.search(r"git", prompt, re.I), "검증자 프롬프트에 git 금지가 없음"
        assert re.search(r"\d+\s*회", prompt), "검증자 프롬프트에 도구 호출 상한이 없음"
        assert re.search(r"인용", prompt), "검증자 프롬프트에 근거 인용 지시가 없음"
        assert not re.search(AUTHOR_REASONING, prompt), "저자의 논리를 검증자에게 넘김"

    assert re.search(r"12", ctx.final_text), "원자료 12건과 문서의 15건 불일치를 보고하지 않음"
    assert ctx.git_status_clean(), f"문서를 고치지 말라고 했는데 파일이 바뀜: {ctx.sh('git status --short').stdout}"
