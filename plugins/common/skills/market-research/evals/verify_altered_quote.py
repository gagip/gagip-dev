"""verify_altered_quote — 사례 인용 대조를 요청하면 대조 스크립트를 돌려 원문과 다른 인용을 찾아내고,
사례 파일을 고치지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/market-research --case verify_altered_quote
"""

import json

PROMPT = "raw/cases.json에 모은 사용자 글 사례들 인용이 원문이랑 맞는지 대조해줘. 파일은 고치지 말고 결과만 알려줘."

RUNS = 3

CASES = [
    {"id": "C01", "source": "sources/C01.txt", "evidence": "원문 저장", "kind": "행동",
     "quotes": ["한 달 금주하고 병원에서 다시 피검사"]},
    {"id": "C02", "source": "sources/C02.txt", "evidence": "스크린샷 판독", "kind": "행동",
     "quotes": ["보건소에서 간기능만 따로 받았는데 2만원"]},
    {"id": "C03", "source": "sources/C03.txt", "evidence": "원문 저장", "kind": "불편",
     "quotes": ["결과지를 서랍에 넣어놨다가 또 꺼내 봐요"]},
]

SCAFFOLD = r"""
mkdir -p raw/sources
printf '지난달 검진에서 간수치가 높았어요. 한 달 금주하고 병원에서 다시   피검사를 받았습니다.\n' > raw/sources/C01.txt
printf '검진 말고 보건소에서 간기능만 따로 받았는데 만원 조금 넘었어요.\n' > raw/sources/C02.txt
printf '의사는 괜찮다는데 결과지를 서랍에 넣어놨다가 또 꺼내 봐요.\n' > raw/sources/C03.txt
cat > raw/cases.json <<'JSON'
""" + json.dumps(CASES, ensure_ascii=False, indent=1) + r"""
JSON
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.bash_ran(r"verify_quotes\.py"), f"대조 스크립트 미사용: {ctx.bash_cmds}"
    assert json.loads(ctx.read("raw/cases.json")) == CASES, "고치지 말라는 사례 파일이 바뀜"
    result = {l.split("\t")[0]: l.split("\t")[2] for l in ctx.read("raw/verify_cases.tsv").splitlines()[1:] if l}
    assert result == {"C01": "일치", "C02": "불일치", "C03": "일치"}, f"대조 결과가 다름: {result}"
    assert ctx.re_search(ctx.final_text, r"C02"), "보고에 불일치 사례 C02가 없음"
