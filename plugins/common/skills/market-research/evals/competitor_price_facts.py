"""competitor_price_facts — 저장해 둔 경쟁 서비스 가격 페이지로 조사하면 가격을 사용자 글 사례와 섞지 않고
제품 사실표(facts.json)에 근거 인용과 함께 적고, 대조 스크립트로 확인하는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/market-research --case competitor_price_facts
"""

import json

PROMPT = (
    "경쟁 서비스 가격을 시장 조사 원자료로 정리해줘. raw/sources/에 세 서비스 요금 페이지를 저장해 뒀어. "
    "인터넷엔 접속하지 말고 저장본만 써. raw/cases.json에는 이미 모은 사용자 글 사례가 있으니 건드리지 마."
)

RUNS = 3

CASES = [{"id": "C01", "source": "sources/post_C01.txt", "evidence": "원문 저장", "kind": "불편",
          "quotes": ["월 구독료가 부담돼서 해지를 고민"]}]

SCAFFOLD = r"""
mkdir -p raw/sources
printf '<html><body><h1>알파 노트 요금제</h1><p>베이직 월 4,900원</p><p>프로 월 9,900원 (연 결제 시 월 7,900원)</p></body></html>\n' > raw/sources/alpha.html
printf '<html><body><h1>베타 메모 가격</h1><p>무료 플랜 제공. 플러스 플랜은 월 6,500원입니다.</p></body></html>\n' > raw/sources/beta.html
printf '<html><body><h1>감마 기록 플랜</h1><p>개인 플랜 월 12,000원, 팀 플랜 사용자당 월 15,000원</p></body></html>\n' > raw/sources/gamma.html
printf '요즘 메모 앱 월 구독료가 부담돼서 해지를 고민 중이에요.\n' > raw/sources/post_C01.txt
cat > raw/cases.json <<'JSON'
""" + json.dumps(CASES, ensure_ascii=False, indent=1) + r"""
JSON
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert not ctx.tool_used("WebFetch") and not ctx.tool_used("WebSearch"), "저장본만 쓰라는데 웹 도구 사용"
    assert json.loads(ctx.read("raw/cases.json")) == CASES, "가격을 사용자 글 사례 파일에 섞음"

    facts = json.loads(ctx.read("raw/facts.json") or "[]")
    assert len(facts) >= 3, f"제품 사실표 항목이 3개 미만: {facts}"
    text = json.dumps(facts, ensure_ascii=False)
    for price in ("4,900", "6,500", "12,000"):
        assert price in text or price.replace(",", "") in text, f"가격 {price}가 사실표에 없음"
    assert all(f.get("quotes") and f.get("source") for f in facts), "근거 인용·출처가 없는 사실 항목"

    assert ctx.bash_ran(r"verify_quotes\.py\s+\S*facts\.json"), f"사실표 대조 미실행: {ctx.bash_cmds}"
    verified = [l.split("\t") for l in ctx.read("raw/verify_facts.tsv").splitlines()[1:] if l]
    assert verified and all(row[2] == "일치" for row in verified), f"사실표 인용이 저장본과 불일치: {verified}"
