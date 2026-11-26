#!/usr/bin/env python3
"""기준 ref 대비 변경이 범위를 지키는지 검사한다(테스트 삭제·skip 추가·단언 감소 등)."""
import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

SKIP_PATTERNS = [
    r"@skip\b", r"pytest\.mark\.skip", r"\.skip\(", r"\bxit\(", r"\bxdescribe\(",
    r"@Disabled\b", r"@Ignore\b", r"\bt\.Skip\(",
]
SKIP_REGEX = re.compile("|".join(SKIP_PATTERNS))
ASSERT_REGEX = re.compile(r"\bassert\w*|\bexpect\(")
DEPENDENCY_NAMES = [
    "package.json", "requirements*.txt", "pyproject.toml", "build.gradle*",
    "Cargo.toml", "go.mod", "*.csproj", "Podfile",
]
TOKEN = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


class GitError(Exception):
    pass


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotepath=off", *args], capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} 실패")
    return result.stdout


def is_test_path(path: str) -> bool:
    tokens = {token.lower() for token in TOKEN.findall(path)}
    return bool(tokens & {"test", "tests", "spec", "specs"})


def changed_files(root: Path, base: str) -> list[tuple[str, str, str]]:
    """(상태, 경로, 옛 경로) 목록. 상태는 A·M·D·R."""
    entries: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for line in git(root, "diff", "-M", "--name-status", base).splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        if status in ("R", "C"):
            entries.append(("R" if status == "R" else "A", parts[2], parts[1]))
            seen.add(parts[2])
        else:
            entries.append((status, parts[1], parts[1]))
            seen.add(parts[1])
    for path in git(root, "ls-files", "--others", "--exclude-standard").splitlines():
        if path not in seen:
            entries.append(("A", path, path))
    return entries


def added_removed_lines(root: Path, base: str, status: str, path: str, old: str) -> tuple[list[str], list[str]]:
    if status == "A" and not _tracked(root, path):
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        return text.splitlines(), []
    diff = git(root, "diff", "-M", "-U0", base, "--", path, old)
    added, removed = [], []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("@@"):
            in_hunk = True
            continue
        if line.startswith("diff --git"):
            in_hunk = False
            continue
        if not in_hunk:
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    return added, removed


def _tracked(root: Path, path: str) -> bool:
    return bool(git(root, "ls-files", "--", path).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="변경이 범위를 지키는지 검사한다.")
    parser.add_argument("--base", required=True, help="비교 기준 ref")
    parser.add_argument("--allow", action="append", default=[], help="허용 경로 glob(여러 번)")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"루트 폴더가 없다: {root}", file=sys.stderr)
        return 2
    try:
        git(root, "rev-parse", "--is-inside-work-tree")
    except GitError as error:
        print(f"git 저장소가 아니다: {error}", file=sys.stderr)
        return 2
    try:
        git(root, "rev-parse", "--verify", "--quiet", f"{args.base}^{{commit}}")
    except GitError:
        print(f"기준 ref가 없다: {args.base}", file=sys.stderr)
        return 2

    errors = 0

    def error(path: str, message: str) -> None:
        nonlocal errors
        errors += 1
        print(f"오류 {path} {message}")

    for status, path, old in changed_files(root, args.base):
        if args.allow and not any(fnmatch.fnmatch(path, glob) for glob in args.allow):
            error(path, "범위 밖")
        if any(fnmatch.fnmatch(Path(path).name, name) for name in DEPENDENCY_NAMES):
            print(f"경고 {path} 의존성 파일이 바뀜")
        if not is_test_path(path):
            continue
        if status == "D":
            error(path, "테스트 파일이 삭제됨")
            continue
        added, removed = added_removed_lines(root, args.base, status, path, old)
        for line in added:
            if SKIP_REGEX.search(line):
                error(path, f"skip 표시가 추가됨: {line.strip()}")
        added_asserts = sum(1 for line in added if ASSERT_REGEX.search(line))
        removed_asserts = sum(1 for line in removed if ASSERT_REGEX.search(line))
        if removed_asserts > added_asserts:
            print(f"경고 {path} 지워진 단언 {removed_asserts}줄 > 추가된 단언 {added_asserts}줄")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
