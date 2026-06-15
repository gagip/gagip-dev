"""목차 슬라이드 (type: toc)

slide 키: (없음 — ctx의 sections에서 자동 생성)

ctx 키:
  position, project_name, sections (list of {no, title, subtitle, position})
"""

from .base import e


def render(slide: dict, ctx: dict) -> str:
    pos = ctx.get('position', 2)
    proj = e(ctx.get('project_name', '프로젝트명'))
    sections = ctx.get('sections', [])

    # 섹션이 없으면 기본 4섹션 표시
    if not sections:
        sections = [
            {'no': '01', 'title': '프로젝트 개요', 'subtitle': '배경 · 목표 · 핵심 기능'},
            {'no': '02', 'title': '개발 현황',     'subtitle': '진행 현황 · 성과 · 아키텍처'},
            {'no': '03', 'title': '상세 &amp; 일정', 'subtitle': '구현 · 산출물 · 비교'},
            {'no': '04', 'title': '기대 효과 &amp; 다음 단계', 'subtitle': '효과 · 로드맵 · Q&amp;A'},
        ]

    cols = '    <div style="flex:1;display:grid;grid-template-columns:1fr 1fr;column-gap:120px;align-content:center;">\n'
    for sec in sections:
        no = e(sec.get('no', '01'))
        title = sec.get('title', '')
        subtitle = sec.get('subtitle', '')
        # title/subtitle는 HTML을 포함할 수 있으므로 이미 이스케이프 완료된 상태로 들어옴
        # (section.py에서 저장 시 e() 적용)
        cols += (
            f'      <div style="display:flex;align-items:baseline;gap:36px;padding:38px 0;border-bottom:1px solid #E4E4E2;">\n'
            f'        <span style="font-family:\'JetBrains Mono\',monospace;font-size:30px;color:#A2A5AB;min-width:54px;">{no}</span>\n'
            f'        <div><div style="font-size:38px;font-weight:600;">{title}</div>'
            + (f'<div style="font-size:23px;color:#6E727A;margin-top:6px;">{subtitle}</div>' if subtitle else '')
            + '</div>\n'
            f'      </div>\n'
        )
    cols += '    </div>'

    return f"""  <section data-label="{pos:02d} 목차" style="background:#FFFFFF;color:#17191F;padding:88px 110px 80px;flex-direction:column;font-family:'Pretendard',sans-serif;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
      <span style="font-family:'JetBrains Mono',monospace;font-size:19px;letter-spacing:0.18em;text-transform:uppercase;color:#6E727A;">Contents</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:19px;color:#A2A5AB;">{pos:02d}</span>
    </div>
    <h2 style="font-size:58px;font-weight:700;letter-spacing:-0.02em;line-height:1.1;margin:18px 0 0;">목차</h2>
    <hr style="height:1px;background:#E4E4E2;border:0;margin:40px 0 0;width:100%;">
{cols}
    <div style="font-family:'JetBrains Mono',monospace;font-size:18px;color:#A2A5AB;letter-spacing:0.04em;">{proj}</div>
  </section>"""
