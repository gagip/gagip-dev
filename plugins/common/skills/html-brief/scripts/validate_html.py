#!/usr/bin/env python3
"""Validate the structural contract of an html-brief artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
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
