"""HTML 세션 문서를 만들고, 디자인 시스템 CSS·갱신 시각을 맞추고, 고정 칸을 검사한다.

사용:
  python3 session_doc.py new <경로.html> --title "<세션 목적>"
  python3 session_doc.py sync <경로.html>     # CSS를 최신으로, 갱신 시각을 지금으로
  python3 session_doc.py check <경로.html>    # 고정 칸·스크립트·CSS 검사
종료 코드: 0 통과, 1 검사 실패, 2 파일을 읽거나 쓸 수 없음.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CSS_PATH = SKILL_DIR / "assets" / "ui.css"
FIXED_IDS = ("state", "spec", "flow")
STATE_KINDS = ("run", "wait", "stop", "ok")
STYLE_RE = re.compile(r'(<style id="ui">)(.*?)(</style>)', re.S)
UPDATED_RE = re.compile(r'(<span id="updated">)(.*?)(</span>)', re.S)

SKELETON = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>세션: {title}</title>
<style id="ui">
{css}</style>
</head>
<body>
<main>
<h1>{title}</h1>
<div class="meta">시작 {today} · 마지막 갱신 <span id="updated">{now}</span></div>

<section id="state"><p><span class="pill run">진행 중</span>{{지금 하는 작업 한 문장}}. 다음: {{다음에 할 일}}.</p></section>

<section id="spec" class="box"><dl class="spec">
 <dt>목표</dt><dd>{{왜 하는지, 무엇을 바꾸는지}}</dd>
 <dt>완료 기준</dt><dd>{{기준마다 증거 종류 하나}}</dd>
 <dt>제약사항</dt><dd>{{건드리지 않을 것, 지킬 규칙}}</dd>
 <dt>비목표</dt><dd>{{이번에 하지 않을 것}}</dd>
 <dt>검증 수단</dt><dd>{{무엇을 돌리고 무엇을 띄워 보나}}</dd>
 <dt>결과물</dt><dd>{{PR·문서·화면과 절대경로}}</dd>
</dl></section>

<ol id="flow" class="flow">
 <li class="now">{{하는 단계}}</li>
 <li>{{남은 단계}}</li>
</ol>

</main>
</body>
</html>
"""


class _Scan(HTMLParser):
    """id가 있는 요소의 등장 순서, 상태 표시 종류, script 태그 수를 모은다."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.scripts = 0
        self.state_pills: list[str] = []
        self._in_state = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self.scripts += 1
        if a.get("id"):
            self.ids.append(a["id"])
        if self._in_state:
            self._in_state += 1
            classes = (a.get("class") or "").split()
            if "pill" in classes:
                self.state_pills += [c for c in classes if c != "pill"]
        elif a.get("id") == "state":
            self._in_state = 1

    def handle_endtag(self, tag):
        if self._in_state:
            self._in_state -= 1


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def problems(text: str, css: str) -> list[str]:
    """세션 문서가 지켜야 할 것을 검사해 어긴 항목을 돌려준다. 빈 목록이면 통과."""
    scan = _Scan()
    scan.feed(text)
    found: list[str] = []
    missing = [i for i in FIXED_IDS if i not in scan.ids]
    if missing:
        found.append(f"고정 칸이 없다: {', '.join('#' + m for m in missing)}")
    else:
        pos = [scan.ids.index(i) for i in FIXED_IDS]
        if pos != sorted(pos):
            found.append("고정 칸 순서가 #state → #spec → #flow가 아니다")
        sections_before = re.search(r"<(section|h2)\b", text[: text.find('id="flow"')].split('id="spec"', 1)[-1])
        if sections_before:
            found.append("#spec과 #flow 사이에 다른 칸이 있다")
    kinds = [k for k in scan.state_pills if k in STATE_KINDS]
    if len(kinds) != 1:
        found.append(f"#state에 상태 표시(pill {'/'.join(STATE_KINDS)})가 정확히 하나여야 한다: {kinds}")
    if scan.scripts:
        found.append(f"<script>가 {scan.scripts}개 있다. 옆 창은 스크립트를 돌리지 않는다")
    m = STYLE_RE.search(text)
    if not m:
        found.append('<style id="ui">가 없다')
    elif m.group(2).strip() != css.strip():
        found.append("디자인 시스템 CSS가 최신이 아니다. sync를 돌린다")
    if not UPDATED_RE.search(text):
        found.append('갱신 시각 <span id="updated">가 없다')
    return found


def sync(text: str, css: str, now: str) -> str:
    """<style id="ui"> 내용을 최신 CSS로, 갱신 시각을 now로 바꾼다."""
    text, n = STYLE_RE.subn(lambda m: f"{m.group(1)}\n{css}{m.group(3)}", text, count=1)
    if n == 0:
        text = text.replace("</head>", f'<style id="ui">\n{css}</style>\n</head>', 1)
    return UPDATED_RE.sub(lambda m: f"{m.group(1)}{now}{m.group(3)}", text, count=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new")
    p_new.add_argument("path", type=Path)
    p_new.add_argument("--title", required=True)
    for name in ("sync", "check"):
        sub.add_parser(name).add_argument("path", type=Path)
    args = ap.parse_args(argv)

    try:
        css = CSS_PATH.read_text(encoding="utf-8")
        if args.cmd == "new":
            if args.path.exists():
                print(f"이미 있다: {args.path}. 이어 쓰려면 sync를 쓴다", file=sys.stderr)
                return 2
            now = _now()
            args.path.parent.mkdir(parents=True, exist_ok=True)
            args.path.write_text(SKELETON.format(title=html.escape(args.title), css=css, today=now[:10], now=now), encoding="utf-8")
            print(f"만듦: {args.path}")
            return 0
        text = args.path.read_text(encoding="utf-8")
        if args.cmd == "sync":
            args.path.write_text(sync(text, css, _now()), encoding="utf-8")
            text = args.path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"파일 오류: {e}", file=sys.stderr)
        return 2

    found = problems(text, css)
    for f in found:
        print(f"[실패] {f}")
    print("통과" if not found else f"실패 {len(found)}개")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
