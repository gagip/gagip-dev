"""개발 진행 현황 슬라이드 (type: roadmap)

slide 키 (인라인 모드):
  phases        - [{label, name, status}] (status: 완료|진행 중|예정)
  progress_pct  - 전체 진행률 0–100

globals 폴백 (프리셋 모드):
  roadmap.{phases, progress_pct}

ctx 키:
  position, section_no, project_name
"""

from .base import e, phase_style, render_eyebrow, render_footer


_DEFAULT_PHASES = [
    {'label': 'PHASE 1', 'name': '기획 · 설계',   'status': '완료'},
    {'label': 'PHASE 2', 'name': '핵심 개발',      'status': '완료'},
    {'label': 'PHASE 3', 'name': '통합 · 테스트',  'status': '진행 중'},
    {'label': 'PHASE 4', 'name': '배포 · 안정화',  'status': '예정'},
]


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 1)
    sec = ctx.get('section_no', '01')
    proj = ctx.get('project_name', '프로젝트명')
    rm_g = ctx.get('globals', {}).get('roadmap', {})

    phases = slide.get('phases') or rm_g.get('phases') or _DEFAULT_PHASES
    progress = slide.get('progress_pct') if slide.get('progress_pct') is not None else rm_g.get('progress_pct', 62.5)

    cols = ''
    for ph in phases:
        st = ph.get('status', '예정')
        ps = phase_style(st)
        cols += (
            f'        <div style="display:flex;flex-direction:column;gap:18px;">\n'
            f'          <div style="width:20px;height:20px;border-radius:50%;{ps["dot"]}margin-top:-19px;"></div>\n'
            f'          <span style="font-family:\'JetBrains Mono\',monospace;font-size:20px;color:{ps["label_color"]}">'
            f'{e(ph.get("label","PHASE"))}</span>\n'
            f'          <div style="{ps["name_style"]}">{e(ph.get("name","단계"))}</div>\n'
            f'          <div style="{ps["status_style"]}">{e(st)}</div>\n'
            f'        </div>\n'
        )

    return f"""  <section data-label="{pos:02d} 진행 현황" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
{render_eyebrow('Roadmap', sec, pos)}
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">개발 진행 현황</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center;">
      <div style="position:relative;height:2px;background:#E4E4E2;margin-bottom:46px;">
        <div style="position:absolute;top:0;left:0;width:{progress}%;height:2px;background:#17191F;"></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat({len(phases)},1fr);gap:48px;">
{cols}      </div>
    </div>
{render_footer(proj)}
  </section>"""
