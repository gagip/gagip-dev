#!/usr/bin/env python3
"""PRODUCT.md·PRD.md·EXPERIMENTS.md가 Product D3 형식을 지키는지 검사한다."""
import argparse
import re
import sys
from pathlib import Path

PRODUCT_SECTIONS = [
    ("Purpose", "목적"),
    ("Target Users", "대상 사용자"),
    ("Core Problems", "핵심 문제"),
    ("Vision", "비전"),
    ("Principles", "원칙"),
    ("Non-goals", "비목표"),
    ("Success Criteria", "성공 기준"),
]
PRD_SECTIONS = [
    ("Purpose", "목적"),
    ("Problem", "문제"),
    ("Scope", "범위"),
    ("Success Criteria", "성공 기준"),
]
EXPERIMENT_FIELDS = ["가설", "방법", "판정선", "결과", "판정"]
HEADING = re.compile(r"^##\s+(.+?)\s*$")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CHECKLIST = re.compile(r"^\s*[-*]\s+\[[ xX]\]")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE = re.compile(r"^\s*(```|~~~)")


def blank_keep_newlines(match: re.Match) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def prepare_lines(text: str) -> list[str]:
    """HTML 주석과 코드 펜스 안을 공백으로 지우되 줄 번호는 유지한다."""
    text = COMMENT.sub(blank_keep_newlines, text)
    lines = text.split("\n")
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            lines[index] = ""
        elif in_fence:
            lines[index] = ""
    return lines


def heading_matches(heading: str, names: tuple[str, str]) -> bool:
    lowered = heading.lower()
    for name in names:
        name = name.lower()
        if lowered == name or re.match(rf"^{re.escape(name)}(\s|\(|:|/)", lowered):
            return True
    return False


def missing_sections(lines: list[str], required: list[tuple[str, str]]) -> list[str]:
    headings = [m.group(1) for line in lines if (m := HEADING.match(line))]
    return [
        names[0] for names in required
        if not any(heading_matches(h, names) for h in headings)
    ]


def check_links(lines: list[str], base: Path) -> list[tuple[int, str]]:
    problems = []
    for number, line in enumerate(lines, start=1):
        for match in LINK.finditer(line):
            target = match.group(1)
            if "<" in target or target.startswith("#") or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            if not (base / path_part).exists():
                problems.append((number, f"링크 대상이 없다: {target}"))
    return problems


def field_values(entry_lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in entry_lines:
        stripped = line.strip().lstrip("-*").strip().replace("**", "")
        for name in EXPERIMENT_FIELDS:
            if re.match(rf"^{name}\s*:", stripped):
                values[name] = stripped.split(":", 1)[1].strip()
                break
    return values


def check_experiments(lines: list[str]) -> list[tuple[int, str]]:
    problems = []
    starts = [i for i, line in enumerate(lines) if HEADING.match(line)]
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        title = HEADING.match(lines[start]).group(1)
        values = field_values(lines[start + 1:end])
        for name in EXPERIMENT_FIELDS:
            if name not in values:
                problems.append((start + 1, f"실험 항목 「{title}」에 {name} 줄이 없다"))
        if values.get("결과") and "판정선" in values and not values["판정선"]:
            problems.append((start + 1, f"실험 항목 「{title}」: 판정선 없이 결과를 적음"))
    return problems


class Report:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors = 0

    def emit(self, level: str, path: Path, line: int, message: str) -> None:
        if level == "오류":
            self.errors += 1
        print(f"{level} {path.relative_to(self.root).as_posix()}:{line} {message}")


def read_lines(path: Path) -> list[str]:
    return prepare_lines(path.read_text(encoding="utf-8"))


def check_document(report: Report, path: Path, sections: list[tuple[str, str]] | None) -> list[str]:
    lines = read_lines(path)
    if sections is not None:
        for name in missing_sections(lines, sections):
            report.emit("오류", path, 1, f"## {name} 제목이 없다")
    for number, message in check_links(lines, path.parent):
        report.emit("오류", path, number, message)
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Product D3 문서 형식을 검사한다.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--product", default="PRODUCT.md")
    parser.add_argument("--features", default="docs/features")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"루트 폴더가 없다: {root}", file=sys.stderr)
        return 2
    report = Report(root)

    product = root / args.product
    if product.is_file():
        check_document(report, product, PRODUCT_SECTIONS)
    else:
        print(f"오류 {args.product}:1 파일이 없다")
        report.errors += 1

    features = root / args.features
    if features.is_dir():
        for prd in sorted(features.glob("*/PRD.md")):
            lines = check_document(report, prd, PRD_SECTIONS)
            for number, line in enumerate(lines, start=1):
                if CHECKLIST.match(line):
                    report.emit("경고", prd, number, "완료 조건은 테스트로 옮기고 PRD에서 반복하지 않는다")
        for log in sorted(features.glob("*/EXPERIMENTS.md")):
            lines = check_document(report, log, None)
            for number, message in check_experiments(lines):
                report.emit("오류", log, number, message)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
