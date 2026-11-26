"""new_project_scaffold — 빈 레포에 D3를 깔면 PRODUCT.md와 AGENTS.md 블록을 만들고 CLAUDE.md는 만들지 않는다."""
from pathlib import Path

PROMPT = "이 빈 레포에 Product D3 깔아줘. 만들 제품은 혼자 사는 직장인이 퇴근길에 살 것을 잊지 않게 하는 장보기 메모 앱이야. 모르는 칸은 미정으로 두고 더 묻지 말고 진행해."
FOLLOWUPS = ["권장안대로 진행해"]
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && git commit -q --allow-empty -m init"
SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    assert ctx.exists("PRODUCT.md"), "PRODUCT.md 없음"
    assert "<!-- product-d3 start -->" in ctx.read("AGENTS.md"), "AGENTS.md에 D3 블록 없음"
    assert not ctx.exists("CLAUDE.md"), "CLAUDE.md를 만듦"
    result = ctx.sh(["python3", str(SCRIPTS / "check_d3_docs.py"), "--root", "."])
    assert result.returncode == 0, f"D3 문서 검사 실패: {result.stdout}"
