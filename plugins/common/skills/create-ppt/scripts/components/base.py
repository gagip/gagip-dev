"""
공통 헬퍼, HTML 템플릿 (HEAD/FOOT), 렌더 유틸
"""

from html import escape as _esc


# ── 데이터 헬퍼 ────────────────────────────────────────────────────────────────

def e(val, default=''):
    """값을 HTML-safe 문자열로 변환"""
    v = val if val is not None else default
    return _esc(str(v)) if v != '' else _esc(str(default))


def g(d, *keys, default=''):
    """중첩 딕셔너리 안전 조회"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


# ── 슬라이드 스타일 헬퍼 ───────────────────────────────────────────────────────

def phase_style(status):
    """로드맵 단계 스타일 결정"""
    if status == '진행 중':
        return {
            'dot': 'background:#17191F; box-shadow:0 0 0 6px #E4E4E2;',
            'label_color': '#17191F; font-weight:600;',
            'name_style': 'font-size:30px; font-weight:700;',
            'status_style': 'font-size:23px; color:#17191F; font-weight:600;',
        }
    elif status == '예정':
        return {
            'dot': 'background:#FFFFFF; border:2px solid #C8CACE;',
            'label_color': '#A2A5AB;',
            'name_style': 'font-size:30px; font-weight:700; color:#A2A5AB;',
            'status_style': 'font-size:23px; color:#A2A5AB;',
        }
    else:  # 완료
        return {
            'dot': 'background:#17191F;',
            'label_color': '#6E727A;',
            'name_style': 'font-size:30px; font-weight:700;',
            'status_style': 'font-size:23px; color:#6E727A;',
        }


def schedule_status_style(status):
    """일정 상태 텍스트 스타일"""
    if status == '진행 중':
        return 'font-weight:700;'
    elif status == '예정':
        return 'color:#A2A5AB; font-weight:600;'
    else:
        return 'font-weight:600;'


def row_opacity(status):
    """일정 행 투명도 (예정 항목은 흐리게)"""
    return ' color:#A2A5AB;' if status == '예정' else ''


# ── 공통 렌더 조각 ─────────────────────────────────────────────────────────────

def render_eyebrow(label, section_no, position):
    """표준 슬라이드 상단 eyebrow (섹션번호·레이블 왼쪽 / 슬라이드 번호 오른쪽)"""
    return (
        f'    <div style="display:flex;justify-content:space-between;align-items:baseline;">\n'
        f'      <span style="font-family:\'JetBrains Mono\',monospace;font-size:19px;'
        f'letter-spacing:0.18em;text-transform:uppercase;color:#6E727A;">'
        f'{section_no} · {label}</span>\n'
        f'      <span style="font-family:\'JetBrains Mono\',monospace;font-size:19px;'
        f'color:#A2A5AB;">{position:02d}</span>\n'
        f'    </div>'
    )


def render_footer(project_name):
    """표준 슬라이드 하단 프로젝트명"""
    return (
        f'    <div style="font-family:\'JetBrains Mono\',monospace;font-size:18px;'
        f'color:#A2A5AB;letter-spacing:0.04em;">{e(project_name)}</div>'
    )


# ── HTML 셸 (HEAD / FOOT) ──────────────────────────────────────────────────────

HEAD = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* {{ box-sizing:border-box;margin:0;padding:0; }}
body {{ background:#111;display:flex;height:100vh;overflow:hidden;font-family:'Pretendard',sans-serif; }}
#sidebar {{ width:200px;flex-shrink:0;background:#1C1C1C;overflow-y:auto;padding:12px 10px;display:flex;flex-direction:column;gap:6px;scrollbar-width:thin;scrollbar-color:#444 transparent; }}
#sidebar::-webkit-scrollbar {{ width:4px; }}
#sidebar::-webkit-scrollbar-thumb {{ background:#444;border-radius:2px; }}
.thumb {{ cursor:pointer;border:2px solid transparent;border-radius:3px;overflow:hidden;flex-shrink:0; }}
.thumb:hover {{ border-color:#666; }}
.thumb.active {{ border-color:#fff; }}
.thumb-frame {{ width:100%;aspect-ratio:16/9;position:relative;overflow:hidden;pointer-events:none; }}
.thumb-frame > section {{ position:absolute;top:0;left:0;width:1920px;height:1080px;transform-origin:top left; }}
.thumb-label {{ font-size:9px;font-family:'JetBrains Mono',monospace;color:#666;padding:3px 4px 4px;background:#1C1C1C;line-height:1; }}
.thumb.active .thumb-label {{ color:#aaa; }}
#stage {{ flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden; }}
#deck {{ position:relative;width:1920px;height:1080px;transform-origin:center center; }}
#deck > section {{ position:absolute;inset:0;width:1920px;height:1080px;display:none; }}
#deck > section.active {{ display:flex !important; }}
#controls {{ position:fixed;bottom:18px;left:50%;transform:translateX(calc(-50% + 100px));display:flex;align-items:center;gap:10px;background:rgba(0,0,0,.75);padding:8px 16px;border-radius:20px;backdrop-filter:blur(8px);z-index:100; }}
#controls button {{ background:none;border:1px solid #555;color:#ccc;padding:5px 14px;border-radius:4px;cursor:pointer;font-family:'JetBrains Mono',monospace;font-size:13px;transition:background .15s,color .15s; }}
#controls button:hover {{ background:rgba(255,255,255,.12);color:#fff; }}
#slide-info {{ font-family:'JetBrains Mono',monospace;font-size:13px;color:#777;min-width:60px;text-align:center; }}
#hint {{ position:fixed;top:14px;right:18px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#444;z-index:100;cursor:pointer;transition:color .15s; }}
#hint:hover {{ color:#888; }}
</style>
</head>
<body>
<div id="sidebar"></div>
<div id="stage"><div id="deck">
"""

FOOT = """\
</div></div>
<div id="controls">
  <button id="btn-prev">← 이전</button>
  <span id="slide-info">1 / {total}</span>
  <button id="btn-next">다음 →</button>
</div>
<div id="hint" title="F 키로 전체화면">⤢ 전체화면</div>
<script>
const deck=document.getElementById('deck'),sidebar=document.getElementById('sidebar'),info=document.getElementById('slide-info');
const slides=Array.from(deck.querySelectorAll(':scope>section'));
const total=slides.length;
let cur=0;
function scale(){{const s=document.getElementById('stage');deck.style.transform=`scale(${{Math.min(s.clientWidth/1920,s.clientHeight/1080)*.96}})`;}}
window.addEventListener('resize',scale);scale();
slides.forEach((s,i)=>{{
  const t=document.createElement('div');t.className='thumb';t.dataset.index=i;
  const f=document.createElement('div');f.className='thumb-frame';
  f.appendChild(s.cloneNode(true));t.appendChild(f);
  const l=document.createElement('div');l.className='thumb-label';
  l.textContent=s.getAttribute('data-label')||`${{i+1}}`;t.appendChild(l);
  t.addEventListener('click',()=>go(i));sidebar.appendChild(t);
}});
function scaleT(){{sidebar.querySelectorAll('.thumb-frame').forEach(f=>{{const sc=f.clientWidth/1920;const el=f.querySelector('section');if(el)el.style.transform=`scale(${{sc}})`;}});}}
window.addEventListener('resize',scaleT);requestAnimationFrame(()=>requestAnimationFrame(scaleT));
function go(i){{
  slides[cur].classList.remove('active');sidebar.querySelectorAll('.thumb')[cur].classList.remove('active');
  cur=Math.max(0,Math.min(total-1,i));
  slides[cur].classList.add('active');
  const th=sidebar.querySelectorAll('.thumb')[cur];th.classList.add('active');th.scrollIntoView({{block:'nearest',behavior:'smooth'}});
  info.textContent=`${{cur+1}} / ${{total}}`;
}}
document.getElementById('btn-prev').onclick=()=>go(cur-1);
document.getElementById('btn-next').onclick=()=>go(cur+1);
document.addEventListener('keydown',ev=>{{
  if(ev.key==='ArrowRight'||ev.key==='ArrowDown'||ev.key===' '){{ev.preventDefault();go(cur+1);}}
  else if(ev.key==='ArrowLeft'||ev.key==='ArrowUp'){{ev.preventDefault();go(cur-1);}}
  else if(ev.key==='f'||ev.key==='F'){{document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}}
  else if(ev.key==='Home')go(0);else if(ev.key==='End')go(total-1);
}});
document.getElementById('hint').onclick=()=>{{document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen();}};
go(0);
</script>
</body></html>
"""
