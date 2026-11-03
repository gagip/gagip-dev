"""blocked_cafe_capture_list — 글 본문이 막힌 카페 출처에서 저장된 검색 결과로 후보를 뽑아 캡처 목록을 만들고,
막힌 본문을 다른 경로로 받으려 하지 않는지 검증.

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/market-research --case blocked_cafe_capture_list
"""

import re

PROMPT = (
    "pages/ 폴더에 네이버 카페 검색 결과 페이지를 저장해 뒀어. 재검 후기 사용자 글을 모으려는데, 카페 글 본문은 "
    "에이전트 브라우저가 막혀 있어서 내가 브라우저로 열고 캡처할게. 저장된 페이지에서 후보를 뽑고 내가 캡처할 목록과 "
    "실행할 명령까지 준비해줘. 인터넷엔 접속하지 말고 현재 디렉터리 안에서만 작업해."
)

RUNS = 3

SCAFFOLD = r"""
mkdir -p pages
cat > pages/01.html <<'HTML'
<ul>
<li class="bx"><a href="https://cafe.naver.com/healthcafe/1001?art=x" class="title_link">간수치 재검 후기 새 창 열림</a>
<a href="https://cafe.naver.com/healthcafe/1001?art=x" class="dsc_link">한 달 금주하고 병원에서 다시 피검사를 받았더니 수치가 내려갔어요</a></li>
<li class="bx"><a href="https://cafe.naver.com/moms/2002" class="title_link">보건소에서 간 검사 따로 받아봤어요</a>
<a href="https://cafe.naver.com/moms/2002" class="dsc_link">검진 말고 보건소에서 간기능만 따로 받았는데 만원 조금 넘었어요</a></li>
<li class="bx"><a href="https://cafe.naver.com/adcafe/3003" class="title_link">간 영양제 최저가 공동구매</a>
<a href="https://cafe.naver.com/adcafe/3003" class="dsc_link">지금 주문하면 30% 할인 이벤트 진행 중입니다 링크 클릭</a></li>
</ul>
HTML
"""


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()} / 툴: {ctx.tool_names()}"
    assert ctx.bash_ran(r"(?s)collect_candidates\.py.*--from-html"), f"후보 수집 스크립트 미사용: {ctx.bash_cmds}"
    executed = [re.sub(r"(?s)<<-?\s*['\"]?(\w+)['\"]?.*?\n\1\b", "", c) for c in ctx.bash_cmds]
    ran_capture = [c for c in executed
                   if ctx.re_search(c, r"python3?\s+(-\S+\s+)*\S*capture_helper\.py(?![^|;&\n]*\s(-h|--help)\b)")]
    assert not ran_capture, f"키 입력을 받는 캡처 도구를 에이전트가 직접 실행함: {ran_capture}"
    assert not ctx.bash_ran(r"(curl|wget|python3?\s+-c).*(cafe\.naver\.com|apis\.naver\.com)"), "막힌 카페 본문·API를 직접 받으려 함"
    assert not ctx.tool_used("WebFetch"), "인터넷 접속 금지인데 WebFetch 사용"

    lists = [p for p in ctx.sh("ls -R").stdout.split() if p.endswith(".tsv")]
    assert any("candidates" in p for p in lists), f"candidates.tsv 없음: {lists}"
    shortlist = ctx.read("**/shortlist.tsv")
    assert shortlist, f"캡처 목록 shortlist.tsv 없음: {lists}"
    header = shortlist.splitlines()[0].split("\t")
    assert {"id", "url"} <= set(header), f"캡처 목록에 id·url 칸이 없음: {header}"
    assert "healthcafe/1001" in shortlist and "moms/2002" in shortlist, "본인 경험 후보가 목록에 없음"
    assert "?art=" not in shortlist, "검색 추적 인자가 남은 주소"
    assert "adcafe/3003" not in shortlist, "광고 글이 캡처 목록에 남음"
    assert ctx.re_search(ctx.final_text, r"capture_helper\.py\s+--list\s+\S*shortlist\.tsv"), "사람에게 줄 캡처 명령(--list shortlist.tsv)이 없음"
