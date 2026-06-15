"""추진 배경 슬라이드 (type: background)

slide 키 (인라인 모드):
  points  - 배경 포인트 문자열 배열 (최대 3개)

globals 폴백 (프리셋 모드):
  background.points

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    '기존 방식의 한계나 고객이 겪던 문제를 짚습니다.',
    '새로운 접근이 필요한 이유를 설명합니다.',
    '이 프로젝트가 해결하는 방향을 제시합니다.',
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    points = (
        slide.get('points')
        or ctx.get('globals', {}).get('background', {}).get('points')
        or _DEFAULTS
    )

    rows = ''
    for i, pt in enumerate(points[:3], 1):
        rows += (
            f'        <div style="display:flex;gap:28px;align-items:flex-start;">\n'
            f'          <span style="font-family:\'JetBrains Mono\',monospace;font-size:24px;'
            f'color:#17191F;font-weight:600;min-width:36px;">{i:02d}</span>\n'
            f'          <p style="font-size:30px;line-height:1.5;margin:0;">{e(pt)}</p>\n'
            f'        </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 배경" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Background', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">추진 배경</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:1fr 1.05fr;column-gap:90px;align-items:center;">
      <div style="display:flex;flex-direction:column;gap:34px;">
{rows}      </div>
      <div style="aspect-ratio:4/3;background:repeating-linear-gradient(135deg,#F2F2F0,#F2F2F0 11px,#ECECEA 11px,#ECECEA 22px);border:1px solid #E4E4E2;display:flex;align-items:center;justify-content:center;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#9A9DA3;letter-spacing:0.08em;">현황 스크린샷 / 도식</span>
      </div>
    </div>
{render_footer(proj)}
  </section>"""
