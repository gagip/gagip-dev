"""게시 전에 문서 본문에서 내부 표현을 찾는다. 걸린 줄이 있으면 종료 코드 1이다.

    python3 check_doc.py <문서 경로>
"""

import re
import sys
from pathlib import Path

WORK_WORDS = r"(?:비평|시안|회의|검토|논의|작업)"
PATTERNS = {
    "로컬 경로": r"(?:/Users/|/home/|~/|[A-Za-z]:\\)",
    "세션 표현": r"(?:세션 문서|이번 세션|서브에이전트|사실표|작업 폴더)",
    "PR·이슈 번호": r"(?:(?<![\w#&])#\d{1,5}(?![0-9A-Za-z])|\bPR\s*\d+)",
    "항목 코드": r"(?<![A-Za-z0-9_-])[A-Z]-?\d{1,3}(?![A-Za-z0-9_])",
    "날짜 꼬리표": (
        rf"(?:\d{{1,2}}/\d{{1,2}}\s*\S*\s*{WORK_WORDS}"
        rf"|\d{{1,2}}월 \d{{1,2}}일\s*\S*\s*{WORK_WORDS}"
        rf"|\d{{4}}-\d{{2}}-\d{{2}}\s*\S*\s*{WORK_WORDS}"
        r"|\d{4}-\d{2}-\d{2}_)"
    ),
    "파일 이름": (
        r"(?!(?:Node|Next|Nuxt|Vue|React)\.js)"
        r"(?<![\w.-])[\w.-]+\.(?:py|ts|tsx|js|jsx|kt|java|swift|sh|json|ya?ml|md|gradle|dart)(?![A-Za-z0-9])"
    ),
    "코드 이름": r"(?<![A-Za-z0-9_])(?:[a-z]+_[a-z0-9_]+|[A-Z]{2,}_[A-Z0-9_]+)(?![A-Za-z0-9_])",
}
HEADING = re.compile(r"^(#{1,6})\s+(.*)")
FOLDED_OPEN = re.compile(r"<(details|toggle|style|script)\b", re.IGNORECASE)
FOLDED_CLOSE = re.compile(r"</(details|toggle|style|script)>", re.IGNORECASE)


def body_lines(text: str):
    """접힌 영역과 「개발 참고」 절을 뺀 (줄 번호, 줄)을 낸다."""
    folded_depth = 0
    dev_heading_level = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if dev_heading_level is not None and level <= dev_heading_level:
                dev_heading_level = None
            if "개발 참고" in heading.group(2):
                dev_heading_level = level
        opened = len(FOLDED_OPEN.findall(line))
        closed = len(FOLDED_CLOSE.findall(line))
        inside = folded_depth > 0 or opened > 0 or dev_heading_level is not None
        folded_depth = max(folded_depth + opened - closed, 0)
        if not inside:
            yield number, line


def find_hits(text: str) -> list[tuple[int, str, str]]:
    hits = []
    for number, line in body_lines(text):
        for kind, pattern in PATTERNS.items():
            match = re.search(pattern, line)
            if match:
                hits.append((number, kind, match.group(0)))
    unclosed = len(FOLDED_OPEN.findall(text)) - len(FOLDED_CLOSE.findall(text))
    if unclosed > 0:
        hits.append((0, "닫히지 않은 접힘", f"{unclosed}개, 그 뒤 본문을 검사하지 못함"))
    return hits


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"문서를 찾지 못함: {path}")
        return 2
    hits = find_hits(path.read_text(encoding="utf-8"))
    for number, kind, found in hits:
        print(f"{path}:{number}: {kind}: {found}")
    print(f"걸린 줄 {len(hits)}건" if hits else "통과")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
