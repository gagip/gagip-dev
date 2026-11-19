"""문서에서 바뀐 줄만 골라 「위치 · 전 · 후」 표 이미지(PNG)와 같은 이름 HTML을 만든다.

실행:
  python3 doc_change_image.py <문서> --out <결과.png>                  # git HEAD와 비교
  python3 doc_change_image.py <문서> --base-file <사본> --out <결과.png> # 고치기 전 사본과 비교

바뀐 줄이 20줄을 넘으면 절(가장 가까운 제목)별로 나눠 <결과>_2.png, <결과>_3.png …를 만든다.
"""
import argparse
import difflib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROWS_PER_IMAGE = 20
PAGE_WIDTH = 1100
PAIR_RATIO = 0.4
TOKEN_RE = re.compile(r"\s+|\w+|[^\w\s]")
MD_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$")
HTML_HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.I)
TAG_RE = re.compile(r"<[^>]+>")
FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
HEIGHT_RE = re.compile(r'data-h="(\d+)"')


@dataclass(frozen=True)
class Row:
    """바뀐 줄 하나. old·new 중 하나가 None이면 지운 줄·새 줄이다."""
    line: int
    section: str
    old: str | None
    new: str | None


def headings(lines: list[str]) -> list[str]:
    """줄마다 그 줄이 속한 가장 가까운 제목(제목 줄은 자기 자신). 코드 블록 안 `#`은 제목이 아니다."""
    current, in_fence, out = "", False, []
    for text in lines:
        if FENCE_RE.match(text):
            in_fence = not in_fence
        elif not in_fence:
            md = MD_HEADING_RE.match(text)
            tag = HTML_HEADING_RE.search(text)
            if md:
                current = md.group(1)
            elif tag:
                current = html.unescape(TAG_RE.sub("", tag.group(1))).strip()
        out.append(current)
    return out


def _pair(old: list[str], new: list[str]) -> list[tuple[int | None, int | None]]:
    """바뀐 덩어리 안에서 순서를 지키며 유사도 합이 가장 큰 짝을 고르고, 짝 없는 줄은 지운 줄·새 줄로 남긴다."""
    n, m = len(old), len(new)
    ratio = [[difflib.SequenceMatcher(None, o, w, autojunk=False).ratio() for w in new] for o in old]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            paired = best[i + 1][j + 1] + ratio[i][j] if ratio[i][j] >= PAIR_RATIO else -1.0
            best[i][j] = max(paired, best[i + 1][j], best[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if ratio[i][j] >= PAIR_RATIO and best[i][j] == best[i + 1][j + 1] + ratio[i][j]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i][j + 1]:
            pairs.append((None, j))
            j += 1
        else:
            pairs.append((i, None))
            i += 1
    pairs.extend((k, None) for k in range(i, n))
    pairs.extend((None, k) for k in range(j, m))
    return pairs


def diff_rows(old_text: str, new_text: str) -> list[Row]:
    """두 본문에서 바뀐 줄만 문서 순서대로 돌려준다. 행 번호는 새 줄이면 후, 지운 줄이면 전 기준이다."""
    # splitlines는 \x0c 등에서도 나눠 편집기 행 번호와 어긋난다.
    old = [s.rstrip("\r") for s in old_text.split("\n")]
    new = [s.rstrip("\r") for s in new_text.split("\n")]
    old_sec, new_sec = headings(old), headings(new)
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        for oi, nj in _pair(old[i1:i2], new[j1:j2]):
            if nj is not None:
                n = j1 + nj
                rows.append(Row(n + 1, new_sec[n], None if oi is None else old[i1 + oi], new[n]))
            else:
                o = i1 + oi
                rows.append(Row(o + 1, old_sec[o], old[o], None))
    return [r for r in rows if (r.old or "").strip() or (r.new or "").strip()]


def word_diff(old: str, new: str) -> tuple[str, str]:
    """한 줄의 전·후를 낱말 단위로 비교해 지운 말은 <del>, 넣은 말은 <ins>로 감싼 HTML을 돌려준다."""
    a, b = TOKEN_RE.findall(old), TOKEN_RE.findall(new)
    left, right = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        before, after = html.escape("".join(a[i1:i2])), html.escape("".join(b[j1:j2]))
        if tag == "equal":
            left.append(before)
            right.append(after)
            continue
        if before:
            left.append(f"<del>{before}</del>")
        if after:
            right.append(f"<ins>{after}</ins>")
    return "".join(left), "".join(right)


def split_pages(rows: list[Row], limit: int = ROWS_PER_IMAGE) -> list[list[Row]]:
    """절이 끊기지 않게 이미지 한 장에 limit줄까지 담는다. 한 절이 limit을 넘으면 그 절만 잘라 나눈다."""
    sections: list[list[Row]] = []
    for row in rows:
        if sections and sections[-1][0].section == row.section:
            sections[-1].append(row)
        else:
            sections.append([row])
    pages: list[list[Row]] = []
    for sec in sections:
        for k in range(0, len(sec), limit):
            chunk = sec[k:k + limit]
            if pages and len(pages[-1]) + len(chunk) <= limit:
                pages[-1].extend(chunk)
            else:
                pages.append(list(chunk))
    return pages


NONE_CELL = '<span class="none">(없음)</span>'
CSS = """
body{margin:0;padding:24px;background:#fff;color:#191f28;font:15px/1.6 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;width:%dpx}
h1{font-size:19px;margin:0 0 4px} p{margin:0 0 14px;color:#4e5968;font-size:13px}
table{border-collapse:collapse;width:100%%;table-layout:fixed} th,td{border:1px solid #e5e8eb;padding:10px 12px;vertical-align:top;text-align:left;word-break:break-all;white-space:pre-wrap}
thead th{background:#f2f4f6;font-size:13px} thead th:first-child,tbody th{width:200px} tbody th{font-size:13px;color:#4e5968;font-weight:600}
del{background:#ffe3e0;color:#b42318} ins{background:#dcfce7;color:#166534;text-decoration:none;font-weight:600}
.none{color:#8b95a1}
""" % PAGE_WIDTH
MEASURE_JS = ("<script>addEventListener('load',()=>{const m=document.createElement('meta');"
              "m.setAttribute('data-h',Math.ceil(document.body.getBoundingClientRect().height));document.head.append(m)})</script>")


def render_html(rows: list[Row], title: str, page: int, pages: int) -> str:
    """표 한 장 HTML. 새 줄은 전 칸, 지운 줄은 후 칸을 「(없음)」으로 둔다."""
    body = []
    for r in rows:
        where = f"{r.line}행" + (f" · {r.section}" if r.section else "")
        if r.old is None:
            before, after = NONE_CELL, f"<ins>{html.escape(r.new)}</ins>"
            where += " · 새 줄"
        elif r.new is None:
            before, after = f"<del>{html.escape(r.old)}</del>", NONE_CELL
            where += " · 지운 줄(전 기준)"
        else:
            before, after = word_diff(r.old, r.new)
        body.append(f"<tr><th>{html.escape(where)}</th><td>{before}</td><td>{after}</td></tr>")
    sub = "빨강 취소선은 지운 말, 초록은 넣은 말."
    if pages > 1:
        sub += f" {page}/{pages}장."
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{CSS}</style></head><body><h1>{html.escape(title)}</h1><p>{sub}</p>"
            "<table><thead><tr><th>위치</th><th>전</th><th>후</th></tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></body></html>")


def find_chrome() -> str | None:
    """CHROME 환경 변수 → macOS 기본 위치 → PATH 순으로 크롬을 찾는다."""
    candidates = [os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")]
    return next((c for c in candidates if c and Path(c).exists()), None)


def screenshot(chrome: str, html_path: Path, png_path: Path) -> str | None:
    """헤드리스 크롬으로 문서 높이를 잰 뒤 그 높이로 배율 2 캡처한다. 실패하면 사유를 돌려준다."""
    base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={PAGE_WIDTH + 48},800"]
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.html"
        probe.write_text(html_path.read_text(encoding="utf-8").replace("</head>", MEASURE_JS + "</head>"), encoding="utf-8")
        dom = subprocess.run([*base, "--dump-dom", probe.as_uri()], capture_output=True, text=True, timeout=60)
    found = HEIGHT_RE.search(dom.stdout)
    if not found:
        return f"높이를 재지 못함: {dom.stderr.strip()[-300:]}"
    shot = subprocess.run([*base[:-1], f"--window-size={PAGE_WIDTH + 48},{found.group(1)}",
                           "--force-device-scale-factor=2", f"--screenshot={png_path}", html_path.as_uri()],
                          capture_output=True, text=True, timeout=60)
    if shot.returncode != 0 or not png_path.exists():
        return f"캡처 실패: {shot.stderr.strip()[-300:]}"
    return None


def git_base(doc: Path, rev: str) -> tuple[str | None, str]:
    """git rev 시점 본문. 그 시점에 파일이 없으면 빈 본문, git 밖이면 None과 사유."""
    top = subprocess.run(["git", "-C", str(doc.parent), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode != 0:
        return None, f"git 저장소 밖이다. --base-file로 고치기 전 사본을 준다: {doc}"
    rel = doc.resolve().relative_to(Path(top.stdout.strip()).resolve()).as_posix()
    verified = subprocess.run(["git", "-C", top.stdout.strip(), "rev-parse", "--verify", "-q", f"{rev}^{{commit}}"],
                              capture_output=True)
    if verified.returncode != 0:
        return None, f"git 시점이 없다: {rev}"
    shown = subprocess.run(["git", "-C", top.stdout.strip(), "show", f"{rev}:{rel}"], capture_output=True)
    return (shown.stdout.decode("utf-8") if shown.returncode == 0 else ""), rev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("doc", type=Path, help="고친 문서")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--base", default="HEAD", help="비교할 git 시점 (기본 HEAD)")
    src.add_argument("--base-file", type=Path, help="고치기 전 사본 파일")
    ap.add_argument("--out", type=Path, required=True, help="결과 PNG 경로. 같은 이름 .html도 만든다")
    ap.add_argument("--title", help="이미지 제목 (기본 「<파일 이름> — 바뀐 줄 N개」)")
    ap.add_argument("--html-only", action="store_true", help="PNG 없이 HTML만 만든다")
    args = ap.parse_args(argv)

    if not args.doc.is_file():
        print(f"실패: 문서가 없다: {args.doc}", file=sys.stderr)
        return 2
    if args.base_file:
        if not args.base_file.is_file():
            print(f"실패: 사본이 없다: {args.base_file}", file=sys.stderr)
            return 2
        old_text, label = args.base_file.read_text(encoding="utf-8"), args.base_file.name
    else:
        old_text, label = git_base(args.doc, args.base)
        if old_text is None:
            print(f"실패: {label}", file=sys.stderr)
            return 2

    rows = diff_rows(old_text, args.doc.read_text(encoding="utf-8"))
    if not rows:
        print(f"바뀐 줄 없음 (기준: {label})")
        return 0

    title = args.title or f"{args.doc.name} — 바뀐 줄 {len(rows)}개"
    pages = split_pages(rows)
    chrome = None if args.html_only else find_chrome()
    if not args.html_only and chrome is None:
        print("실패: 크롬을 찾지 못함. CHROME 환경 변수로 경로를 주거나 --html-only로 HTML만 만든다", file=sys.stderr)
        return 2
    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    for k, page_rows in enumerate(pages, 1):
        png = args.out if k == 1 else args.out.with_name(f"{args.out.stem}_{k}{args.out.suffix}")
        page_html = png.with_suffix(".html")
        page_html.write_text(render_html(page_rows, title, k, len(pages)), encoding="utf-8")
        if chrome:
            error = screenshot(chrome, page_html, png)
            if error:
                print(f"실패: {error} (HTML은 남김: {page_html})", file=sys.stderr)
                return 1
        outputs.append(png if chrome else page_html)

    print(f"바뀐 줄 {len(rows)}개 (기준: {label})")
    print(outputs[0])
    if len(outputs) > 1:
        print(f"나머지 {len(outputs) - 1}장: " + ", ".join(str(p) for p in outputs[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
