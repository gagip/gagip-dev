"""기대 효과 슬라이드 (type: impact)

slide 키 (인라인 모드):
  text  - 핵심 기대 효과 한 문장

globals 폴백 (프리셋 모드):
  impact  (문자열)

ctx 키:
  position, section_no
"""

from .base import e


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')

    text = e(
        slide.get('text')
        or ctx.get('globals', {}).get('impact')
        or '이 프로젝트로 고객이 얻는 가장 큰 가치를 한 문장으로 분명하게 정리합니다.'
    )

    return f"""  <section data-label="{pos:02d} 기대 효과" style="background:#F6F6F4;color:#17191F;padding:88px 130px 80px;flex-direction:column;justify-content:center;font-family:'Pretendard',sans-serif;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:19px;letter-spacing:0.18em;text-transform:uppercase;color:#6E727A;">{sec} · Impact</span>
    <p style="font-size:60px;font-weight:600;letter-spacing:-0.02em;line-height:1.4;margin:40px 0 0;max-width:1500px;">{text}</p>
    <div style="font-family:'JetBrains Mono',monospace;font-size:22px;color:#6E727A;margin-top:48px;letter-spacing:0.04em;">— 핵심 기대 효과</div>
  </section>"""
