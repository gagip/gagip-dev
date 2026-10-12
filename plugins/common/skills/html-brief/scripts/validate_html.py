#!/usr/bin/env python3
"""Validate the structural contract of an html-brief artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


def parse_span(raw: str | None, default: int, limit: int) -> int:
    match = re.match(r"[\t\n\f\r ]*\+?([0-9]+)", raw or "")
    if not match:
        return default
    digits = match.group(1).lstrip("0") or "0"
    return limit if len(digits) > len(str(limit)) else min(int(digits), limit)


class TableShape:
    def __init__(self, line: int) -> None:
        self.line = line
        self.section = "tbody"
        self.head_width = 0
        self.body_rows: list[tuple[int, int]] = []
        self.row_line: int | None = None
        self.row_cells = 0
        self.row_width = 0
        self.spans_below: list[int] = []
        self.spans_to_section_end = 0

    def start_section(self, section: str) -> None:
        self.end_row()
        self.section = section
        self.spans_below = []
        self.spans_to_section_end = 0

    def start_row(self, line: int) -> None:
        self.end_row()
        self.row_line = line
        self.row_cells = 0
        self.row_width = self.spans_to_section_end + (self.spans_below.pop(0) if self.spans_below else 0)

    def add_cell(self, line: int, colspan: int, rowspan: int) -> None:
        if self.row_line is None:
            self.start_row(line)
        self.row_cells += 1
        self.row_width += colspan
        if rowspan == 0:
            self.spans_to_section_end += colspan
        for offset in range(rowspan - 1):
            if offset == len(self.spans_below):
                self.spans_below.append(0)
            self.spans_below[offset] += colspan

    def end_row(self) -> None:
        if self.row_line is None:
            return
        if self.section == "thead":
            self.head_width = max(self.head_width, self.row_width)
        elif self.row_cells and self.section == "tbody":
            self.body_rows.append((self.row_line, self.row_width))
        self.row_line = None

    def width_mismatch(self) -> str | None:
        self.end_row()
        mismatched = [(line, width) for line, width in self.body_rows if width != self.head_width]
        if not self.head_width or not mismatched:
            return None
        line, width = mismatched[0]
        return (
            f"{self.line}줄 표의 머리는 {self.head_width}칸인데 본문 {len(mismatched)}개 줄의 칸 수가 다릅니다"
            f"(첫 줄: {line}줄 {width}칸)."
        )


class BriefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.has_viewport = False
        self.title_parts: list[str] = []
        self.in_title = False
        self.main_count = 0
        self.h1_count = 0
        self.source_links = 0
        self.in_brief_data = False
        self.brief_data_parts: list[str] = []
        self.tables: list[TableShape] = []
        self.table_warnings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "table":
            self.tables.append(TableShape(self.getpos()[0]))
        elif self.tables:
            table = self.tables[-1]
            if tag in {"thead", "tbody", "tfoot"}:
                table.start_section(tag)
            elif tag == "tr":
                table.start_row(self.getpos()[0])
            elif tag in {"td", "th"}:
                colspan = max(1, parse_span(values.get("colspan"), 1, 1000))
                rowspan = parse_span(values.get("rowspan"), 1, 65534)
                table.add_cell(self.getpos()[0], colspan, rowspan)

        if tag == "html":
            self.lang = values.get("lang") or ""
        elif tag == "meta" and (values.get("name") or "").lower() == "viewport":
            self.has_viewport = bool(values.get("content"))
        elif tag == "title":
            self.in_title = True
        elif tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "a" and (values.get("href") or "").startswith(("https://", "http://")):
            self.source_links += 1
        elif tag == "script" and values.get("id") == "brief-data":
            if values.get("type") == "application/json":
                self.in_brief_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self.tables:
            mismatch = self.tables.pop().width_mismatch()
            if mismatch:
                self.table_warnings.append(mismatch)
        elif self.tables and tag in {"thead", "tbody", "tfoot"}:
            self.tables[-1].start_section("tbody")
        elif self.tables and tag == "tr":
            self.tables[-1].end_row()

        if tag == "title":
            self.in_title = False
        elif tag == "script" and self.in_brief_data:
            self.in_brief_data = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_brief_data:
            self.brief_data_parts.append(data)


def validate(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.is_file():
        return [f"파일을 찾을 수 없습니다: {path}"], warnings

    text = path.read_text(encoding="utf-8")
    parser = BriefParser()
    try:
        parser.feed(text)
    except Exception as exc:  # HTMLParser errors are unusual but actionable.
        return [f"HTML을 읽을 수 없습니다: {exc}"], warnings

    if not re.match(r"^\s*<!doctype\s+html>", text, flags=re.IGNORECASE):
        errors.append("HTML5 doctype이 없습니다.")
    if not parser.lang:
        errors.append("html 요소의 lang 속성이 없습니다.")
    if not "".join(parser.title_parts).strip():
        errors.append("비어 있지 않은 title 요소가 필요합니다.")
    if not parser.has_viewport:
        errors.append("모바일 viewport 메타 태그가 없습니다.")
    if parser.main_count != 1:
        errors.append(f"main 요소는 하나여야 합니다. 현재 {parser.main_count}개입니다.")
    if parser.h1_count != 1:
        errors.append(f"h1 요소는 하나여야 합니다. 현재 {parser.h1_count}개입니다.")
    if re.search(r"\{\{[A-Z][A-Z0-9_]*\}\}", text):
        errors.append("치환되지 않은 템플릿 플레이스홀더가 있습니다.")
    if "@media print" not in text:
        warnings.append("인쇄용 @media print 규칙이 없습니다.")
    if "overflow-x" not in text:
        warnings.append("넓은 표의 내부 가로 스크롤 규칙을 확인하세요.")
    if parser.source_links == 0:
        warnings.append("HTTP(S) 원문 링크가 없습니다. 내부 자료만 사용했다면 무시할 수 있습니다.")
    warnings.extend(parser.table_warnings)

    raw_json = "".join(parser.brief_data_parts).strip()
    if not raw_json:
        errors.append('application/json 형식의 script#brief-data가 없습니다.')
        return errors, warnings

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        errors.append(f"brief-data JSON이 유효하지 않습니다: {exc}")
        return errors, warnings

    required = {"document", "mode", "asOf", "audience", "summary", "sources"}
    missing = sorted(required - set(data))
    if missing:
        errors.append("brief-data 필수 필드가 없습니다: " + ", ".join(missing))
    if data.get("mode") not in {"decision", "report"}:
        errors.append('brief-data.mode는 "decision" 또는 "report"여야 합니다.')
    if not isinstance(data.get("audience"), list) or not data.get("audience"):
        errors.append("brief-data.audience는 비어 있지 않은 배열이어야 합니다.")
    if not isinstance(data.get("sources"), dict):
        errors.append("brief-data.sources는 출처 ID를 키로 갖는 객체여야 합니다.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="검사할 HTML 파일")
    args = parser.parse_args()

    errors, warnings = validate(args.html.resolve())
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(errors)}개 오류, {len(warnings)}개 경고", file=sys.stderr)
        return 1

    print(f"PASS: html-brief 구조 유효 ({len(warnings)}개 경고)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
