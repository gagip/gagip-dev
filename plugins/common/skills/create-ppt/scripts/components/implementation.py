"""구현 상세 슬라이드 (type: implementation)

slide 키 (인라인 모드):
  description  - 핵심 로직 설명 텍스트
  points       - 처리 흐름 포인트 배열
  code         - 코드 스니펫 문자열

globals 폴백 (프리셋 모드):
  implementation.{description, points, code}

ctx 키:
  position, section_no, project_name
"""

from html import escape as _esc
from .base import e, g, render_eyebrow, render_footer


_DEFAULT_CODE = (
    '// 핵심 처리 예시\n'
    'async function process(req) {\n'
    '  const data = await fetch(url);\n'
    '  return transform(data);\n'
    '}'
)


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')
    impl_g = ctx.get('globals', {}).get('implementation', {})

    desc   = e(slide.get('description') or impl_g.get('description') or '핵심 로직이 어떻게 동작하는지 한 문단으로 설명합니다.')
    points = slide.get('points') or impl_g.get('points') or ['처리 흐름의 포인트 1', '처리 흐름의 포인트 2', '처리 흐름의 포인트 3']
    code_raw = slide.get('code') or impl_g.get('code') or _DEFAULT_CODE

    pts = ''
    for pt in points:
        pts += (
            f'          <div style="display:flex;gap:18px;align-items:baseline;">'
            f'<span style="font-family:\'JetBrains Mono\',monospace;font-size:22px;color:#17191F;">·</span>'
            f'<span style="font-size:25px;color:#6E727A;">{e(pt)}</span></div>\n'
        )

    code_html = _esc(code_raw)

    return f"""  <section data-label="{pos:02d} 구현 상세" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Implementation', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">구현 상세</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:grid;grid-template-columns:1fr 1.3fr;column-gap:80px;align-items:center;">
      <div style="display:flex;flex-direction:column;gap:30px;">
        <p style="font-size:30px;font-weight:500;line-height:1.5;margin:0;">{desc}</p>
        <div style="display:flex;flex-direction:column;gap:16px;">
{pts}        </div>
      </div>
      <div style="background:#17191F;padding:38px 42px;">
        <div style="display:flex;gap:9px;margin-bottom:26px;"><span style="width:13px;height:13px;border-radius:50%;background:#3A3D44;display:inline-block;"></span><span style="width:13px;height:13px;border-radius:50%;background:#3A3D44;display:inline-block;"></span><span style="width:13px;height:13px;border-radius:50%;background:#3A3D44;display:inline-block;"></span></div>
        <pre style="margin:0;font-family:'JetBrains Mono',monospace;font-size:20px;line-height:1.7;color:#E8E8E6;white-space:pre-wrap;word-break:break-all;">{code_html}</pre>
      </div>
    </div>
{render_footer(proj)}
  </section>"""
