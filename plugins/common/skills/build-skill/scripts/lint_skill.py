#!/usr/bin/env python3
"""스킬 구조를 정적으로 점검한다. LLM을 부르지 않으므로 비용 없이 먼저 돌릴 수 있다.

    python3 lint_skill.py <스킬디렉토리> [<스킬디렉토리> ...]
    python3 lint_skill.py --all [<스캔루트>]    # 루트 아래 SKILL.md가 있는 모든 스킬 (기본: cwd)

점검 항목은 Agent Skills 작성 모범 사례의 체크리스트 중 기계로 판정되는 것만 담았다.
3인칭 여부, 용어 일관성, 예시의 구체성은 문장 판단이 필요해 여기서 다루지 않는다.

- name: 64자 이하, 소문자·숫자·하이픈, 예약어(claude, anthropic) 금지, 디렉터리명과 일치
- description: 비어 있지 않음, 1,024자 이하, XML 태그 없음
- 본문(frontmatter 제외) 500줄 미만
- SKILL.md의 마크다운 링크가 실제 파일을 가리킴
- 링크된 참조 파일이 다시 다른 참조 파일을 링크하지 않음 (한 단계 깊이)
- 100줄을 넘는 참조 파일은 앞부분에 목차
- 백슬래시 경로 금지

종료 코드: 위반이 없으면 0, 있으면 1, 입력 오류면 2.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_MAX = 64
DESCRIPTION_MAX = 1024
BODY_MAX_LINES = 500
TOC_REQUIRED_LINES = 100
TOC_SEARCH_LINES = 30
RESERVED_WORDS = ("anthropic", "claude")

_NAME_RE = re.compile(r"^[a-z0-9-]+$")
_XML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
_BACKSLASH_PATH_RE = re.compile(r"\b(?:scripts|references|assets|evals)\\[\w.-]")
_TOC_HEADING_RE = re.compile(r"(?mi)^#{1,6}\s*(?:목차|차례|contents|table of contents)\s*$")
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def split_frontmatter(text: str) -> tuple[str, str] | None:
    """(frontmatter, 본문). 시작 --- 와 닫는 --- 가 없으면 None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None


def parse_frontmatter(front: str) -> dict[str, str]:
    """최상위 key: value만 읽는다. `>`·`|` 블록과 들여쓴 이어쓰기를 한 줄로 합친다."""
    fields: dict[str, str] = {}
    key: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if key is not None:
            fields[key] = " ".join(p for p in parts if p).strip()

    for raw in front.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if m and not raw[0].isspace():
            flush()
            key = m.group(1)
            value = m.group(2).strip()
            parts = [] if value in (">", "|", ">-", "|-") else [value.strip("\"'")]
        elif key is not None:
            parts.append(raw.strip())
    flush()
    return fields


def _links(text: str) -> list[str]:
    """코드 블록·인라인 코드 밖의 상대 경로 마크다운 링크."""
    stripped = _INLINE_CODE_RE.sub("", _CODE_FENCE_RE.sub("", text))
    out = []
    for target in _LINK_RE.findall(stripped):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        out.append(target.split("#", 1)[0])
    return [t for t in out if t]


def lint(skill_dir: Path) -> list[str]:
    """위반 메시지 목록. 비어 있으면 통과."""
    skill_dir = skill_dir.resolve()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"SKILL.md가 없다: {skill_dir}"]

    text = skill_md.read_text(encoding="utf-8")
    problems: list[str] = []

    parsed = split_frontmatter(text)
    if parsed is None:
        return ["frontmatter(--- 로 감싼 YAML)가 없다"]
    front, body = parsed
    fields = parse_frontmatter(front)

    name = fields.get("name", "")
    if not name:
        problems.append("name이 비어 있다")
    else:
        if len(name) > NAME_MAX:
            problems.append(f"name이 {NAME_MAX}자를 넘는다 ({len(name)}자)")
        if not _NAME_RE.match(name):
            problems.append(f"name은 소문자·숫자·하이픈만 쓴다: {name!r}")
        for word in RESERVED_WORDS:
            if word in name:
                problems.append(f"name에 예약어 {word!r}를 쓸 수 없다: {name!r}")
        if name != skill_dir.name:
            problems.append(f"name {name!r}이 디렉터리명 {skill_dir.name!r}과 다르다")

    description = fields.get("description", "")
    if not description:
        problems.append("description이 비어 있다")
    else:
        if len(description) > DESCRIPTION_MAX:
            problems.append(f"description이 {DESCRIPTION_MAX}자를 넘는다 ({len(description)}자)")
        if _XML_TAG_RE.search(description):
            problems.append("description에 XML 태그를 쓸 수 없다")

    body_lines = len(body.strip().splitlines())
    if body_lines >= BODY_MAX_LINES:
        problems.append(
            f"본문이 {BODY_MAX_LINES}줄 이상이다 ({body_lines}줄) — references/로 나눈다")

    if _BACKSLASH_PATH_RE.search(text):
        problems.append("백슬래시 경로가 있다 — Windows에서도 슬래시를 쓴다")

    for target in dict.fromkeys(_links(body)):
        resolved = (skill_dir / target).resolve()
        if not resolved.exists():
            problems.append(f"링크 대상이 없다: {target}")
            continue
        if resolved.suffix != ".md" or skill_dir not in resolved.parents:
            continue
        ref_text = resolved.read_text(encoding="utf-8")
        nested = [t for t in dict.fromkeys(_links(ref_text))
                  if (resolved.parent / t).resolve().suffix == ".md"
                  and (resolved.parent / t).resolve() != resolved]
        if nested:
            problems.append(
                f"{target}가 다른 참조 파일을 다시 링크한다 ({', '.join(nested)}) — "
                "참조는 SKILL.md에서 한 단계까지만 둔다")
        lines = ref_text.splitlines()
        if len(lines) > TOC_REQUIRED_LINES:
            head = "\n".join(lines[:TOC_SEARCH_LINES])
            if not _TOC_HEADING_RE.search(head):
                problems.append(
                    f"{target}가 {len(lines)}줄인데 앞부분에 목차(## 목차 또는 ## Contents)가 없다")

    return problems


def discover(root: Path) -> list[Path]:
    out = []
    for skill_md in root.rglob("SKILL.md"):
        if any(part.startswith(".") for part in skill_md.relative_to(root).parts):
            continue
        if any(part.endswith("-eval-runs") for part in skill_md.relative_to(root).parts):
            continue
        out.append(skill_md.parent)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="스킬 구조 정적 점검")
    ap.add_argument("paths", nargs="*", type=Path,
                    help="스킬 디렉토리들. --all이면 스캔 루트 (기본: cwd)")
    ap.add_argument("--all", action="store_true", help="루트 아래 모든 스킬을 점검")
    args = ap.parse_args()

    if args.all:
        root = (args.paths[0] if args.paths else Path.cwd()).resolve()
        skill_dirs = discover(root)
    else:
        skill_dirs = args.paths
    if not skill_dirs:
        print("오류: 점검할 스킬이 없다", file=sys.stderr)
        return 2

    failed = 0
    for skill_dir in skill_dirs:
        problems = lint(skill_dir)
        label = skill_dir.name if args.all else str(skill_dir)
        if problems:
            failed += 1
            print(f"✗ {label}")
            for p in problems:
                print(f"    - {p}")
        else:
            print(f"✓ {label}")
    if len(skill_dirs) > 1:
        print(f"\n{len(skill_dirs) - failed}/{len(skill_dirs)} 통과")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
