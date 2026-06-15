"""마무리 슬라이드 (type: closing)

slide 키 (인라인 모드):
  contact  - 담당자 이름 · 이메일

globals 폴백 (프리셋 모드):
  closing_contact  (문자열)

ctx 키:
  position, project_name, date
"""

from .base import e


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    proj = e(ctx.get('project_name', '프로젝트명'))
    date = e(ctx.get('date', '2026'))

    contact = e(
        slide.get('contact')
        or ctx.get('globals', {}).get('closing_contact')
        or '이름 · 이메일'
    )

    return f"""  <section data-label="{pos:02d} 마무리" style="background:#17191F;color:#FFFFFF;padding:96px 110px 84px;flex-direction:column;justify-content:space-between;font-family:'Pretendard',sans-serif;">
    <div style="font-family:'JetBrains Mono',monospace;font-size:19px;letter-spacing:0.18em;text-transform:uppercase;color:#A2A5AB;">Thank You</div>
    <div>
      <div style="width:64px;height:3px;background:#FFFFFF;margin-bottom:40px;"></div>
      <h2 style="font-size:96px;font-weight:700;letter-spacing:-0.03em;line-height:1.05;margin:0;">감사합니다</h2>
      <p style="font-size:32px;color:#A2A5AB;line-height:1.5;margin:32px 0 0;">질문이 있으시면 언제든 말씀해 주세요.</p>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:flex-end;font-family:'JetBrains Mono',monospace;font-size:20px;color:#C8CACE;letter-spacing:0.04em;">
      <div>{contact}</div>
      <div>{proj} · {date}</div>
    </div>
  </section>"""
