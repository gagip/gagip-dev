"""프로젝트 개요 슬라이드 (type: overview)

slide 키 (인라인 모드):
  summary, detail, period, scope, team, status

globals 폴백 (프리셋 모드):
  overview.{summary, detail, period, scope, team, status}

ctx 키:
  position, section_no, project_name
"""

from .base import e, g, render_eyebrow, render_footer


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')
    ov_g = ctx.get('globals', {}).get('overview', {})

    def get(key, default=''):
        return slide.get(key) or ov_g.get(key) or default

    summary = e(get('summary', '한 문단으로 프로젝트의 목적과 범위를 설명합니다.'))
    detail  = e(get('detail',  '핵심 가치나 차별점을 간단히 덧붙입니다.'))
    period  = e(get('period',  '기간 미정'))
    scope   = e(get('scope',   '범위 미정'))
    team    = e(get('team',    '팀 구성 미정'))
    status  = get('status', '진행 중')
    status_w = '700' if status in ('진행 중', '완료') else '600'

    return f"""  <section data-label="{pos:02d} 개요" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Overview', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">프로젝트 개요</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:1.4fr 1fr;column-gap:96px;align-content:center;">
      <div>
        <p style="font-size:34px;font-weight:500;line-height:1.55;margin:0;">{summary}</p>
        <p style="font-size:26px;color:#6E727A;line-height:1.6;margin:34px 0 0;">{detail}</p>
      </div>
      <div style="display:flex;flex-direction:column;">
        <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #E4E4E2;"><span style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#6E727A;">기간</span><span style="font-size:26px;font-weight:600;">{period}</span></div>
        <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #E4E4E2;"><span style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#6E727A;">범위</span><span style="font-size:26px;font-weight:600;">{scope}</span></div>
        <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #E4E4E2;"><span style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#6E727A;">팀</span><span style="font-size:26px;font-weight:600;">{team}</span></div>
        <div style="display:flex;justify-content:space-between;padding:24px 0;border-top:1px solid #E4E4E2;border-bottom:1px solid #E4E4E2;"><span style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#6E727A;">상태</span><span style="font-size:26px;font-weight:{status_w};">{e(status)}</span></div>
      </div>
    </div>
{render_footer(proj)}
  </section>"""
