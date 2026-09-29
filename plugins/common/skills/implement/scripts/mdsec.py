"""마크다운 산출물에서 절·목록·표를 읽는다.

관문과 평가가 같은 방식으로 산출물을 읽어야 판정이 갈리지 않는다.
읽는 규칙을 한 곳에 두는 이유가 그것이다.
"""

from __future__ import annotations

import re


def section_span(text: str, title: str) -> tuple[int, int] | None:
    """절 본문의 시작·끝. 읽기와 상태 저장이 같은 경계를 사용한다."""
    m = re.search(rf"^(#{{2,3}})\s*{re.escape(title)}\s*$", text, re.MULTILINE)
    if not m:
        return None
    level = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.MULTILINE)
    return m.end(), m.end() + nxt.start() if nxt else len(text)


def section(text: str, title: str) -> str | None:
    """`## title` 아래 본문. 다음 같은 수준 제목 전까지. 없으면 None."""
    span = section_span(text, title)
    return text[span[0]:span[1]] if span is not None else None


def bullets(body: str) -> list[str]:
    """`-` 또는 `*` 목록 항목의 본문. 중첩 항목도 포함한다."""
    return [
        m.group(1).strip()
        for m in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", body, re.MULTILINE)
        if m.group(1).strip()
    ]


def table_rows(body: str) -> list[list[str]]:
    """파이프 표의 데이터 행. 헤더와 구분선은 뺀다."""
    rows: list[list[str]] = []
    for raw in body.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line[1:-1].split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows[1:] if len(rows) > 1 else []


def table_header(body: str) -> list[str]:
    """파이프 표의 헤더 행."""
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            return [c.strip() for c in line[1:-1].split("|")]
    return []


def front_matter(text: str) -> dict[str, str]:
    """`---`로 감싼 평평한 `key: value` 머리말. 없으면 빈 dict.

    핸드오프 파서(handoff.py)와 달리 여기서는 필수 키를 강제하지 않는다.
    핸드오프는 사이클의 상태 정본이라 어긋나면 멈춰야 하지만,
    평가 태스크 정의는 우리가 쓰는 설명 파일이라 강제 수준이 다르다.
    """
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$", line.rstrip())
        if km:
            out[km.group(1)] = km.group(2).strip()
    return out
