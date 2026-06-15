"""기술 스택 슬라이드 (type: tech_stack)

slide 키 (인라인 모드):
  items  - [{category, stack}]

globals 폴백 (프리셋 모드):
  tech_stack  (배열)

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    {'category': 'FRONTEND',  'stack': 'React · TypeScript · Vite'},
    {'category': 'BACKEND',   'stack': 'Node.js · Express'},
    {'category': 'DATABASE',  'stack': 'PostgreSQL · Redis'},
    {'category': 'INFRA',     'stack': 'Docker · AWS · CI/CD'},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    items = (
        slide.get('items')
        or ctx.get('globals', {}).get('tech_stack')
        or _DEFAULTS
    )

    rows = ''
    for item in items:
        rows += (
            f'      <div style="padding:30px 0;border-bottom:1px solid #E4E4E2;'
            f'display:flex;align-items:baseline;gap:32px;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:20px;'
            f'color:#6E727A;min-width:130px;">{e(item.get("category",""))}</span>'
            f'<span style="font-size:28px;font-weight:500;">{e(item.get("stack",""))}</span></div>\n'
        )

    cols = 2 if len(items) > 2 else 1

    return f"""  <section data-label="{pos:02d} 기술 스택" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Tech Stack', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">기술 스택</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:repeat({cols},1fr);column-gap:96px;align-content:center;">
{rows}    </div>
{render_footer(proj)}
  </section>"""
