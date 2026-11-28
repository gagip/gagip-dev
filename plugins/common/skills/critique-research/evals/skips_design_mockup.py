"""skips_design_mockup — 디자인 시안 비평 요청에는 발동하지 않는지 검증 (description의 경계).

    python3 <build-skill>/scripts/run_skill_test.py plugins/common/skills/critique-research --case skips_design_mockup
"""

PROMPT = "mockup.html 시안 비평해줘. 버튼 배치랑 위계가 괜찮은지 봐 줘. 파일은 고치지 마."

RUNS = 3

SCAFFOLD = r"""
git init -q && git config user.name t && git config user.email t@t
cat > mockup.html <<'HTML'
<!doctype html><html><body>
<header><h1>결제</h1></header>
<main><p>합계 12,000원</p><button>취소</button><button>결제하기</button></main>
</body></html>
HTML
git add -A && git commit -qm init
"""


def check(ctx):
    assert not ctx.skill_fired(), f"시안 비평에 발동함: {ctx.skill_invocations()}"
    assert ctx.git_status_clean(), "파일을 고치지 말라고 했는데 바뀜"
