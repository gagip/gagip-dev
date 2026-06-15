"""일정 및 산출물 슬라이드 (type: schedule)

slide 키 (인라인 모드):
  items  - [{phase, deliverables, period, status}]

globals 폴백 (프리셋 모드):
  schedule  (배열)

ctx 키:
  position, section_no, project_name
"""

from .base import e, schedule_status_style, row_opacity, render_eyebrow, render_footer


_DEFAULTS = [
    {'phase': '기획',   'deliverables': '요구사항 정의서 · 화면 설계', 'period': '2026.01 – 02', 'status': '완료'},
    {'phase': '개발',   'deliverables': '핵심 기능 · API · 관리자',   'period': '2026.03 – 05', 'status': '완료'},
    {'phase': '테스트', 'deliverables': '통합 테스트 · QA 리포트',    'period': '2026.06',      'status': '진행 중'},
    {'phase': '배포',   'deliverables': '운영 환경 배포 · 인수인계',  'period': '2026.07',      'status': '예정'},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    items = (
        slide.get('items')
        or ctx.get('globals', {}).get('schedule')
        or _DEFAULTS
    )

    rows = ''
    for item in items:
        st = item.get('status', '예정')
        row_col  = row_opacity(st)
        st_style = schedule_status_style(st)
        rows += (
            f'      <div style="display:grid;grid-template-columns:1.1fr 2fr 1.4fr 1fr;'
            f'padding:30px 0;border-bottom:1px solid #E4E4E2;align-items:center;font-size:27px;{row_col}">\n'
            f'        <span style="font-weight:600;">{e(item.get("phase",""))}</span>\n'
            f'        <span>{e(item.get("deliverables",""))}</span>\n'
            f'        <span style="color:#6E727A;">{e(item.get("period",""))}</span>\n'
            f'        <span style="text-align:right;{st_style}">{e(st)}</span>\n'
            f'      </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 일정 표" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Schedule', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">일정 및 산출물</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
      <div style="display:grid;grid-template-columns:1.1fr 2fr 1.4fr 1fr;padding:22px 0;border-bottom:2px solid #17191F;font-family:'JetBrains Mono',monospace;font-size:20px;letter-spacing:0.04em;color:#6E727A;">
        <span>단계</span><span>산출물</span><span>일정</span><span style="text-align:right;">상태</span>
      </div>
{rows}    </div>
{render_footer(proj)}
  </section>"""
