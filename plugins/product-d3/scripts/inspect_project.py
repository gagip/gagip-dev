#!/usr/bin/env python3
"""프로젝트 루트를 읽기 전용으로 훑어 Product D3 도입에 필요한 사실을 JSON으로 출력한다."""
import argparse
import json
import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {"node_modules", ".git", "build", "dist"}
TEST_DIR_NAMES = {"test", "tests", "__tests__", "androidTest"}
MAX_DEPTH = 4
BUILD_FILE_NAMES = [
    "package.json", "pyproject.toml", "requirements.txt", "build.gradle",
    "build.gradle.kts", "Cargo.toml", "go.mod", "Makefile", "project.godot",
]
NPM_SCRIPTS = ["typecheck", "lint", "test", "build"]
MAKE_TARGETS = ["test", "lint"]


def detect_mode(root: Path) -> str:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts or path.name == ".DS_Store":
            continue
        if path.is_file():
            return "existing"
    return "new"


def find_test_dirs(root: Path) -> list[str]:
    found: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > MAX_DEPTH:
            return
        for child in sorted(directory.iterdir()):
            if not child.is_dir() or child.name in EXCLUDED_DIRS:
                continue
            relative = child.relative_to(root).as_posix()
            if child.name in TEST_DIR_NAMES or relative.endswith("src/test"):
                found.append(relative)
            walk(child, depth + 1)

    walk(root, 1)
    return found


def find_build_files(root: Path) -> list[str]:
    names = [name for name in BUILD_FILE_NAMES if (root / name).is_file()]
    names += [p.name for p in root.glob("settings.gradle*") if p.is_file()]
    names += [p.name for p in root.glob("*.csproj") if p.is_file()]
    return sorted(set(names))


def npm_commands(root: Path) -> list[dict]:
    package = root / "package.json"
    if not package.is_file():
        return []
    try:
        scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(scripts, dict):
        return []
    return [
        {"command": f"npm run {name}", "source": "package.json"}
        for name in NPM_SCRIPTS if name in scripts
    ]


def make_commands(root: Path) -> list[dict]:
    makefile = root / "Makefile"
    if not makefile.is_file():
        return []
    text = makefile.read_text(encoding="utf-8", errors="replace")
    return [
        {"command": f"make {target}", "source": "Makefile"}
        for target in MAKE_TARGETS
        if re.search(rf"^{target}\s*:", text, re.MULTILINE)
    ]


def verify_commands(root: Path) -> list[dict]:
    commands = npm_commands(root) + make_commands(root)
    if (root / "pyproject.toml").is_file():
        commands.append({"command": "python3 -m pytest", "source": "pyproject.toml"})
    elif (root / "tests").is_dir() and (
        (root / "requirements.txt").is_file() or any((root / "tests").glob("*.py"))
    ):
        commands.append({"command": "python3 -m pytest", "source": "tests/"})
    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file():
        commands.append({"command": "./gradlew test", "source": "build.gradle"})
    if (root / "Cargo.toml").is_file():
        commands.append({"command": "cargo test", "source": "Cargo.toml"})
    if (root / "go.mod").is_file():
        commands.append({"command": "go test ./...", "source": "go.mod"})
    return commands


def inspect(root: Path) -> dict:
    files = {
        name: (name if (root / name).is_file() else None)
        for name in ["PRODUCT.md", "AGENTS.md", "CLAUDE.md", "README.md"]
    }
    return {
        "mode": detect_mode(root),
        "files": files,
        "feature_prds": sorted(
            p.relative_to(root).as_posix() for p in root.glob("docs/features/*/PRD.md")
        ),
        "test_dirs": find_test_dirs(root),
        "build_files": find_build_files(root),
        "verify_commands": verify_commands(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="프로젝트 상태를 JSON으로 출력한다.")
    parser.add_argument("root", help="프로젝트 루트 폴더")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        print(f"입력 경로가 폴더가 아니거나 없다: {root}", file=sys.stderr)
        return 2
    print(json.dumps(inspect(root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
