"""핵심 기능 슬라이드 (type: features)

slide 키 (인라인 모드):
  items  - 기능 목록 [{id, name, desc, highlight}] (최대 3개)

globals 폴백 (프리셋 모드):
  features  (배열)

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    {'id': 'F-01', 'name': '기능 이름', 'desc': '이 기능이 고객에게 주는 가치를 한두 문장으로 설명합니다.', 'highlight': False},
    {'id': 'F-02', 'name': '기능 이름', 'desc': '이 기능이 고객에게 주는 가치를 한두 문장으로 설명합니다.', 'highlight': False},
    {'id': 'F-03', 'name': '강조 기능', 'desc': '가장 중요한 기능은 잉크 블록으로 대비를 주어 강조합니다.', 'highlight': True},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    items = (
        slide.get('items')
        or ctx.get('globals', {}).get('features')
        or _DEFAULTS
    )

    cards = ''
    for f in items[:3]:
        is_hi = f.get('highlight', False)
        if is_hi:
            bg      = 'background:#17191F;color:#FFFFFF;'
            id_col  = 'color:#9A9DA3;'
            desc_col = 'color:#C8CACE;'
        else:
            bg      = 'border:1px solid #E4E4E2;'
            id_col  = 'color:#A2A5AB;'
            desc_col = 'color:#6E727A;'

        cards += (
            f'      <div style="{bg}padding:44px 40px;display:flex;flex-direction:column;height:100%;">\n'
            f'        <span style="font-family:\'JetBrains Mono\',monospace;font-size:22px;{id_col}">'
            f'{e(f.get("id", "F-0?"))}</span>\n'
            f'        <h3 style="font-size:36px;font-weight:700;margin:54px 0 0;letter-spacing:-0.01em;">'
            f'{e(f.get("name", "기능 이름"))}</h3>\n'
            f'        <p style="font-size:25px;line-height:1.5;margin:18px 0 0;{desc_col}">'
            f'{e(f.get("desc", "설명"))}</p>\n'
            f'      </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 핵심 기능" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Features', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">핵심 기능</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:32px;align-content:center;">
{cards}    </div>
{render_footer(proj)}
  </section>"""
