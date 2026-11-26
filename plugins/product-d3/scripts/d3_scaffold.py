#!/usr/bin/env python3
"""Product D3 문서·실험 폴더 뼈대를 만든다. 이미 있는 파일은 덮어쓰지 않는다."""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
MARKER = "<!-- product-d3 start -->"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Writer:
    def __init__(self, root: Path, dry_run: bool) -> None:
        self.root = root
        self.dry_run = dry_run

    def _label(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def create(self, path: Path, content: str) -> None:
        if path.exists():
            print(f"건너뜀 {self._label(path)}")
            return
        print(f"만듦 {self._label(path)}")
        if self.dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append(self, path: Path, content: str) -> None:
        print(f"덧붙임 {self._label(path)}")
        if self.dry_run:
            return
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)


def template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def init(writer: Writer, verify_command: str | None) -> None:
    root = writer.root
    writer.create(root / "PRODUCT.md", template("PRODUCT.md"))
    docs = root / "docs"
    if not docs.exists() or (docs.is_dir() and not any(docs.iterdir())):
        writer.create(docs / ".gitkeep", "")
    else:
        print("건너뜀 docs/")
    block = template("AGENTS-block.md").replace("{verify_command}", verify_command or "없음")
    agents = root / "AGENTS.md"
    if not agents.exists():
        writer.create(agents, block)
        return
    print("건너뜀 AGENTS.md")
    if MARKER in agents.read_text(encoding="utf-8"):
        print("이미 있음: AGENTS.md에 product-d3 블록이 있다")
    else:
        print("## 병합 제안")
        print(block)


def feature(writer: Writer, slug: str) -> int:
    if not SLUG_PATTERN.match(slug):
        print(f"slug는 소문자·숫자·하이픈만 쓴다: {slug}", file=sys.stderr)
        return 2
    path = writer.root / "docs" / "features" / slug / "PRD.md"
    writer.create(path, template("PRD.md").replace("{feature}", slug))
    return 0


def experiment(writer: Writer, slug: str, feature_name: str, day: str) -> int:
    if not SLUG_PATTERN.match(slug) or not SLUG_PATTERN.match(feature_name):
        print("slug와 feature는 소문자·숫자·하이픈만 쓴다", file=sys.stderr)
        return 2
    if not DATE_PATTERN.match(day):
        print(f"날짜 형식은 YYYY-MM-DD: {day}", file=sys.stderr)
        return 2
    root = writer.root
    values = {"{feature}": feature_name, "{date}": day, "{slug}": slug}

    def fill(text: str) -> str:
        for key, value in values.items():
            text = text.replace(key, value)
        return text

    writer.create(
        root / "experiments" / f"{day}-{slug}" / "README.md",
        fill(template("experiment-README.md")),
    )
    log = root / "docs" / "features" / feature_name / "EXPERIMENTS.md"
    heading = f"## {day} {slug}"
    entry = fill(template("EXPERIMENTS-entry.md"))
    if not log.exists():
        writer.create(log, "# Experiments\n" + entry)
        return 0
    existing = log.read_text(encoding="utf-8")
    if any(line.strip() == heading for line in existing.splitlines()):
        print(f"건너뜀 {log.relative_to(root).as_posix()} (항목 있음: {heading})")
        return 0
    prefix = "" if existing.endswith("\n") else "\n"
    writer.append(log, prefix + entry)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Product D3 뼈대를 만든다.")
    parser.add_argument("--root", default=".", help="프로젝트 루트(기본: 현재 폴더)")
    parser.add_argument("--dry-run", action="store_true", help="만들지 않고 계획만 출력")
    # 하위 명령 뒤에 써도 받는다. SUPPRESS라 하위 명령 쪽에서 안 쓰면 최상위 값이 남는다.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS)
    common.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init", parents=[common])
    p_init.add_argument("--verify-command")
    p_feature = sub.add_parser("feature", parents=[common])
    p_feature.add_argument("slug")
    p_exp = sub.add_parser("experiment", parents=[common])
    p_exp.add_argument("slug")
    p_exp.add_argument("--feature", required=True)
    p_exp.add_argument("--date", default=None)
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"루트 폴더가 없다: {root}", file=sys.stderr)
        return 2
    writer = Writer(root, args.dry_run)
    if args.command == "init":
        init(writer, args.verify_command)
        return 0
    if args.command == "feature":
        return feature(writer, args.slug)
    if args.command == "experiment":
        day = args.date or date.today().isoformat()
        try:
            date.fromisoformat(day)
        except ValueError:
            print(f"날짜 형식이 틀렸다(YYYY-MM-DD): {day}", file=sys.stderr)
            return 2
        return experiment(writer, args.slug, args.feature, day)
    raise AssertionError(f"알 수 없는 하위 명령: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
