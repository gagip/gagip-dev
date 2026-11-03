"""화면을 바꾸는 요청이면 2단계 계획에 시안 소스 값과 기준 없는 자리를 화면 기준으로 적는다."""

import re

PROMPT = """Badge 컴포넌트(src/Badge.tsx)를 mockup/badge.html 시안대로 바꾸고, 시안에 없는 '값이 없을 때' 상태도 추가해줘. dev 스킬로 진행하고, 웹·외부에 올리지 마."""
RUNS = 1
SCAFFOLD = r"""
git init -q && git config user.email e@e.com && git config user.name E
mkdir -p src mockup
cat > src/Badge.tsx <<'X'
export function Badge({ count }: { count: number }) {
  return <span style={{ padding: "2px 4px", borderRadius: 4 }}>{count}</span>;
}
X
cat > mockup/badge.html <<'X'
<style>.badge{padding:6px 10px;border-radius:999px;background:#E6F4EA;color:#137333;font-size:13px}</style>
<span class="badge">12</span>
X
git add -A && git commit -qm "chore: init"
"""


def plan_text(ctx):
    docs = [p.read_text(encoding="utf-8") for p in ctx.workdir.rglob("*.md") if ".git" not in p.parts]
    return "\n".join(docs + [ctx.final_text])


def check(ctx):
    assert ctx.skill_fired(), f"미발동: {ctx.skill_invocations()}"
    plan = plan_text(ctx)
    start = plan.find("화면 기준")
    assert start >= 0, "계획에 화면 기준이 없음"
    rest = plan[start:]
    nxt = re.search(r"(?m)^#+ ", rest[1:])
    section = rest[: nxt.start() + 1] if nxt else rest
    assert "badge.html" in plan, "계획에 시안 경로가 없음"
    values = [v for v in ("6px", "10px", "999px", "#137333", "#E6F4EA", "13px") if v.lower() in section.lower()]
    assert len(values) >= 2, f"시안 소스에서 읽은 값이 2개 미만: {values}"
    assert re.search(r"기준 없음", section), "시안에 없는 상태를 기준 없음으로 적지 않음"
    assert ctx.sh("git status --porcelain -- src").stdout.strip() == "", "계획 단계에서 코드를 바꿈"
