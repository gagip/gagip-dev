#!/usr/bin/env python3
"""플러그인 폴더를 임시 폴더에 복사해, 문서 안 상대경로가 사본 안에서 풀리는지 검사한다."""
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK = re.compile(r"`([^`\n]+)`")
PATH_LIKE = re.compile(r"^[\w.@\-/]+$")
EXTENSIONS = (".md", ".py", ".html", ".json", ".sh", ".css", ".txt")
PROJECT_PREFIXES = ("docs/", "src/", "tests/", "experiments/", "plugins/")
PROJECT_FILE_NAMES = {"PRODUCT.md", "PRD.md", "AGENTS.md", "CLAUDE.md", "EXPERIMENTS.md"}
FENCE = re.compile(r"^\s*(```|~~~)")


def strip_fences(text: str) -> list[str]:
    lines = text.split("\n")
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
            lines[index] = ""
        elif in_fence:
            lines[index] = ""
    return lines


def candidates(line: str) -> list[str]:
    found = []
    for match in LINK.finditer(line):
        found.append(match.group(1).split("#", 1)[0])
    for match in BACKTICK.finditer(line):
        text = match.group(1)
        if "/" in text and text.endswith(EXTENSIONS) and PATH_LIKE.match(text):
            found.append(text)
    return [item for item in found if item]


def should_skip(target: str) -> bool:
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or "://" in target:
        return True
    if target.startswith(("/", "~")):
        return True
    if any(char in target for char in "<{*$"):
        return True
    normalized = target[2:] if target.startswith("./") else target
    if normalized.startswith(PROJECT_PREFIXES):
        return True
    return "/" not in normalized and normalized in PROJECT_FILE_NAMES


def skill_root(file: Path, plugin_root: Path) -> Path | None:
    current = file.parent
    while True:
        if (current / "SKILL.md").is_file():
            return current
        if current == plugin_root or current == current.parent:
            return None
        current = current.parent


def resolves(target: str, file: Path, plugin_root: Path) -> bool:
    bases = [file.parent]
    if not target.startswith("../"):
        skill = skill_root(file, plugin_root)
        if skill is not None:
            bases.append(skill)
        bases.append(plugin_root)
    for base in bases:
        resolved = (base / target).resolve()
        if resolved.is_relative_to(plugin_root.resolve()) and resolved.exists():
            return True
    return False


def check(plugin_root: Path) -> list[str]:
    problems = []
    for file in sorted(plugin_root.rglob("*.md")):
        if file.name == "CHANGELOG.md":
            continue
        lines = strip_fences(file.read_text(encoding="utf-8", errors="replace"))
        for number, line in enumerate(lines, start=1):
            for target in candidates(line):
                if should_skip(target):
                    continue
                if not resolves(target, file, plugin_root):
                    relative = file.relative_to(plugin_root).as_posix()
                    problems.append(f"안 풀림 {relative}:{number} {target}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="플러그인 단독 설치 시 깨지는 경로를 찾는다.")
    parser.add_argument("plugin_dir")
    args = parser.parse_args()
    source = Path(args.plugin_dir)
    if not source.is_dir():
        print(f"플러그인 폴더가 없다: {source}", file=sys.stderr)
        return 2
    if not any(source.rglob("*.md")):
        print(f"검사할 .md 파일이 없다: {source}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / source.resolve().name
        shutil.copytree(source, copy, symlinks=True)
        problems = check(copy)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
