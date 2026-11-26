"""draft_marks_unknown — 초안은 말하지 않은 칸을 지어내지 않고 미정·(가설)로 둔다."""
import re
from pathlib import Path

PROMPT = "PRODUCT.md 초안 써줘. 대상은 혼자 사는 직장인, 문제는 퇴근길에 살 것을 잊는다는 거야. 나머지는 아직 몰라. 묻지 말고 써."
RUNS = 3
SCAFFOLD = "git init -q && git config user.name t && git config user.email t@t && mkdir -p src && printf 'items = []\n' > src/app.py && git add -A && git commit -qm init"
SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    product = ctx.read("PRODUCT.md")
    assert product, "PRODUCT.md를 쓰지 않음"
    assert re.search(r"미정|\(가설\)", product), "모르는 칸을 미정·(가설)로 두지 않음"
    assert not re.search(r"\d+\s*%", product), "말하지 않은 수치를 지어냄"
    result = ctx.sh(["python3", str(SCRIPTS / "check_d3_docs.py"), "--root", "."])
    assert result.returncode == 0, f"D3 문서 검사 실패: {result.stdout}"
