"""도입 전후 비교 슬라이드 (type: before_after)

slide 키 (인라인 모드):
  before  - 도입 전 항목 배열
  after   - 도입 후 항목 배열

globals 폴백 (프리셋 모드):
  before_after.{before, after}

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULT_BEFORE = ['수작업으로 처리하던 업무', '느린 처리 속도와 잦은 오류', '파편화된 데이터 관리']
_DEFAULT_AFTER  = ['자동화된 처리 파이프라인', '40% 빨라진 속도, 오류 최소화', '통합된 단일 데이터 흐름']


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')
    ba_g = ctx.get('globals', {}).get('before_after', {})

    before = slide.get('before') or ba_g.get('before') or _DEFAULT_BEFORE
    after  = slide.get('after')  or ba_g.get('after')  or _DEFAULT_AFTER

    before_rows = ''.join(
        f'<div style="font-size:28px;color:#6E727A;line-height:1.45;">{e(b)}</div>'
        for b in before
    )
    after_rows = ''.join(
        f'<div style="font-size:28px;line-height:1.45;">{e(a)}</div>'
        for a in after
    )

    return f"""  <section data-label="{pos:02d} 비교" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Before / After', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">도입 전후 비교</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:1fr 1fr;gap:32px;align-content:center;">
      <div style="border:1px solid #E4E4E2;padding:48px 46px;display:flex;flex-direction:column;gap:28px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:20px;letter-spacing:0.1em;color:#A2A5AB;">BEFORE · 도입 전</span>
        <div style="display:flex;flex-direction:column;gap:22px;">{before_rows}</div>
      </div>
      <div style="background:#17191F;color:#FFFFFF;padding:48px 46px;display:flex;flex-direction:column;gap:28px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:20px;letter-spacing:0.1em;color:#9A9DA3;">AFTER · 도입 후</span>
        <div style="display:flex;flex-direction:column;gap:22px;">{after_rows}</div>
      </div>
    </div>
{render_footer(proj)}
  </section>"""
