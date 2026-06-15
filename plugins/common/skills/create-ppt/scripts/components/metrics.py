"""주요 성과 지표 슬라이드 (type: metrics)

slide 키 (인라인 모드):
  items  - [{value, unit, name, note}] (최대 3개)

globals 폴백 (프리셋 모드):
  metrics  (배열)

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    {'value': '98',  'unit': '%',  'name': '테스트 커버리지', 'note': '목표 95% 초과 달성'},
    {'value': '120', 'unit': 'ms', 'name': '평균 응답 시간',  'note': '이전 대비 40% 단축'},
    {'value': '24',  'unit': '개', 'name': '완료된 기능',     'note': '전체 32개 중'},
]

_PAD_MAP = {
    1: ['padding:0;'],
    2: ['padding:0 56px 0 0;border-right:1px solid #E4E4E2;', 'padding:0 0 0 56px;'],
    3: [
        'padding:0 56px 0 0;border-right:1px solid #E4E4E2;',
        'padding:0 56px;border-right:1px solid #E4E4E2;',
        'padding:0 0 0 56px;',
    ],
}


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    items = (
        slide.get('items')
        or ctx.get('globals', {}).get('metrics')
        or _DEFAULTS
    )
    items = items[:3]
    n = len(items)
    paddings = _PAD_MAP.get(n, _PAD_MAP[3])

    cols = ''
    for i, m in enumerate(items):
        unit_size = '64px' if len(str(m.get('unit', ''))) == 1 else '48px'
        cols += (
            f'      <div style="{paddings[i] if i < len(paddings) else ""}">\n'
            f'        <div style="font-size:140px;font-weight:700;letter-spacing:-0.04em;line-height:0.95;">'
            f'{e(m.get("value","–"))}'
            f'<span style="font-size:{unit_size};color:#6E727A;">{e(m.get("unit",""))}</span></div>\n'
            f'        <div style="font-size:28px;font-weight:600;margin-top:26px;">{e(m.get("name","지표"))}</div>\n'
            f'        <div style="font-size:23px;color:#6E727A;margin-top:8px;">{e(m.get("note",""))}</div>\n'
            f'      </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 성과 지표" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Metrics', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">주요 성과 지표</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:repeat({n},1fr);align-content:center;">
{cols}    </div>
{render_footer(proj)}
  </section>"""
