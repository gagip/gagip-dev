"""표지 슬라이드 (type: cover)

slide 키:
  subtitle  - 부제 (선택)

ctx 키:
  project_name, date, presenter, position
"""

from .base import e


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    proj_raw = ctx.get('project_name', '프로젝트명을\n여기에 입력하세요')
    proj_html = e(proj_raw).replace('\n', '<br>')
    date = e(ctx.get('date', '2026.06'))
    presenter = e(ctx.get('presenter', '발표자 · 소속'))
    subtitle = e(
        slide.get('subtitle')
        or ctx.get('globals', {}).get('subtitle', '개발 진행 현황과 핵심 기능을 고객에게 브리핑하기 위한 발표 자료')
    )

    return f"""  <section data-label="{pos:02d} 표지" style="background:#17191F;color:#FFFFFF;padding:96px 110px 84px;flex-direction:column;justify-content:space-between;font-family:'Pretendard',sans-serif;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:19px;letter-spacing:0.18em;text-transform:uppercase;color:#A2A5AB;">Development Briefing</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:19px;letter-spacing:0.12em;color:#A2A5AB;">{date}</div>
    </div>
    <div style="max-width:1400px;">
      <div style="width:64px;height:3px;background:#FFFFFF;margin-bottom:40px;"></div>
      <h1 style="font-size:104px;font-weight:700;letter-spacing:-0.03em;line-height:1.04;margin:0;">{proj_html}</h1>
      <p style="font-size:34px;font-weight:400;color:#A2A5AB;line-height:1.45;margin:34px 0 0;max-width:1080px;">{subtitle}</p>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:flex-end;font-family:'JetBrains Mono',monospace;font-size:20px;color:#C8CACE;letter-spacing:0.04em;">
      <div>{presenter}</div>
      <div>고객 브리핑용</div>
    </div>
  </section>"""
