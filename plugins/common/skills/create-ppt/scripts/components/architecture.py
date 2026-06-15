"""시스템 아키텍처 슬라이드 (type: architecture)

slide 키 (인라인 모드):
  layers  - [{label, name, highlight?}]

globals 폴백 (프리셋 모드):
  architecture.layers

ctx 키:
  position, section_no, project_name
"""

from .base import e, render_eyebrow, render_footer


_DEFAULTS = [
    {'label': 'CLIENT',  'name': '웹 · 앱'},
    {'label': 'GATEWAY', 'name': 'API 서버'},
    {'label': 'CORE',    'name': '비즈니스 로직', 'highlight': True},
    {'label': 'DATA',    'name': 'DB · 캐시'},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')

    layers = (
        slide.get('layers')
        or ctx.get('globals', {}).get('architecture', {}).get('layers')
        or _DEFAULTS
    )

    blocks = ''
    for i, layer in enumerate(layers):
        is_hi = layer.get('highlight', False)
        style   = 'background:#17191F;color:#FFFFFF;' if is_hi else 'border:1px solid #E4E4E2;'
        lbl_col = 'color:#9A9DA3;' if is_hi else 'color:#A2A5AB;'
        blocks += (
            f'        <div style="flex:1;{style}padding:40px 28px;text-align:center;">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:19px;{lbl_col}">'
            f'{e(layer.get("label",""))}</div>'
            f'<div style="font-size:30px;font-weight:700;margin-top:14px;">{e(layer.get("name",""))}</div></div>'
        )
        if i < len(layers) - 1:
            blocks += '\n        <div style="font-family:\'JetBrains Mono\',monospace;font-size:30px;color:#C8CACE;padding:0 22px;">→</div>'
        blocks += '\n'

    return f"""  <section data-label="{pos:02d} 아키텍처" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Architecture', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">시스템 아키텍처</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:flex;align-items:center;justify-content:center;">
      <div style="display:flex;align-items:center;width:100%;">
{blocks}      </div>
    </div>
    <div style="font-size:24px;color:#6E727A;text-align:center;margin-bottom:8px;">복잡한 구성도는 별도 이미지로 대체하세요 — 위 블록은 흐름 요약용입니다.</div>
{render_footer(proj)}
  </section>"""
