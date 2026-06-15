"""다음 단계 슬라이드 (type: next_steps)

slide 키 (인라인 모드):
  steps  - [{name, deadline}]

globals 폴백 (프리셋 모드):
  next_steps  (배열)

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    {'name': '통합 테스트 완료 및 QA',        'deadline': '~ 2026.06'},
    {'name': '운영 환경 배포 및 안정화',       'deadline': '~ 2026.07'},
    {'name': '인수인계 및 운영 가이드 전달',   'deadline': '2026.07'},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    steps = (
        slide.get('steps')
        or ctx.get('globals', {}).get('next_steps')
        or _DEFAULTS
    )

    rows = ''
    for i, step in enumerate(steps, 1):
        rows += (
            f'      <div style="display:flex;align-items:center;gap:40px;padding:34px 0;border-bottom:1px solid #E4E4E2;">\n'
            f'        <span style="font-family:\'JetBrains Mono\',monospace;font-size:26px;'
            f'color:#17191F;font-weight:600;min-width:60px;">{i:02d}</span>\n'
            f'        <div style="font-size:34px;font-weight:600;">{e(step.get("name",""))}</div>\n'
            f'        <span style="margin-left:auto;font-family:\'JetBrains Mono\',monospace;'
            f'font-size:22px;color:#6E727A;">{e(step.get("deadline",""))}</span>\n'
            f'      </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 다음 단계" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Next Steps', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">다음 단계</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
{rows}    </div>
{render_footer(proj)}
  </section>"""
