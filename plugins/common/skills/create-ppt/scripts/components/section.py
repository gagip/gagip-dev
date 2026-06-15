"""섹션 구분 슬라이드 (type: section)

slide 키:
  title    - 섹션 제목 (필수)
  subtitle - 섹션 부제 (선택)

ctx 키:
  position, section_no
"""

from .base import e


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    no_str = ctx.get('section_no', '01')
    title = slide.get('title', f'섹션 {no_str}')
    subtitle = slide.get('subtitle', '')

    subtitle_html = (
        f'\n    <p style="font-size:30px;color:#6E727A;margin:28px 0 0;max-width:1000px;line-height:1.5;">{e(subtitle)}</p>'
        if subtitle else ''
    )

    return f"""  <section data-label="{pos:02d} 섹션 {no_str}" style="background:#F6F6F4;color:#17191F;padding:88px 110px 80px;flex-direction:column;justify-content:center;font-family:'Pretendard',sans-serif;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:200px;font-weight:500;line-height:1;color:#E4E4E2;letter-spacing:-0.02em;">{no_str}</div>
    <h2 style="font-size:80px;font-weight:700;letter-spacing:-0.025em;margin:24px 0 0;">{e(title)}</h2>{subtitle_html}
  </section>"""
