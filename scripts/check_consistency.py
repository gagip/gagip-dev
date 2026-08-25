#!/usr/bin/env python3
"""Validate duplicated plugin metadata and documented skill inventories."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_ROOT = ROOT / "plugins"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
BANNED_RUNTIME_TOKENS = ("$ARGUMENTS", "SKILL_DIR")


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{path.relative_to(ROOT)}: JSON을 읽을 수 없음 ({error})")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)}: 최상위 값이 객체가 아님")
        return {}
    return value


def plugin_dirs() -> list[Path]:
    return sorted(
        path
        for path in PLUGINS_ROOT.iterdir()
        if path.is_dir() and (path / ".claude-plugin" / "plugin.json").is_file()
    )


def validate_manifests(plugins: list[Path], errors: list[str]) -> None:
    for plugin in plugins:
        claude = load_json(plugin / ".claude-plugin" / "plugin.json", errors)
        codex = load_json(plugin / ".codex-plugin" / "plugin.json", errors)
        for field in ("name", "version", "description"):
            if claude.get(field) != codex.get(field):
                errors.append(
                    f"plugins/{plugin.name}: Claude/Codex manifest `{field}` 불일치 "
                    f"({claude.get(field)!r} != {codex.get(field)!r})"
                )
        if claude.get("name") != plugin.name:
            errors.append(
                f"plugins/{plugin.name}: manifest name이 디렉터리명과 다름 "
                f"({claude.get('name')!r})"
            )


def validate_marketplaces(plugins: list[Path], errors: list[str]) -> None:
    expected = {path.name for path in plugins}
    claude = load_json(CLAUDE_MARKETPLACE, errors)
    codex = load_json(CODEX_MARKETPLACE, errors)

    if claude.get("name") != codex.get("name"):
        errors.append("두 marketplace의 `name`이 다름")

    claude_entries = {
        item.get("name"): item
        for item in claude.get("plugins", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    codex_entries = {
        item.get("name"): item
        for item in codex.get("plugins", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if set(claude_entries) != expected:
        errors.append(
            f"Claude marketplace 플러그인 목록 불일치: {sorted(claude_entries)} != {sorted(expected)}"
        )
    if set(codex_entries) != expected:
        errors.append(
            f"Codex marketplace 플러그인 목록 불일치: {sorted(codex_entries)} != {sorted(expected)}"
        )

    for plugin in plugins:
        name = plugin.name
        claude_entry = claude_entries.get(name, {})
        codex_entry = codex_entries.get(name, {})
        if claude_entry.get("source") != f"./plugins/{name}":
            errors.append(f"Claude marketplace `{name}` source 경로가 잘못됨")
        source = codex_entry.get("source")
        if not isinstance(source, dict) or source.get("path") != f"./plugins/{name}":
            errors.append(f"Codex marketplace `{name}` source.path가 잘못됨")


def documented_skills(readme: Path) -> set[str]:
    in_skills = False
    result: set[str] = set()
    for line in readme.read_text(encoding="utf-8").splitlines():
        if line.strip() == "## 스킬":
            in_skills = True
            continue
        if in_skills and line.startswith("## "):
            break
        if not in_skills:
            continue
        match = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if match:
            result.add(match.group(1))
    return result


def validate_skills(plugins: list[Path], errors: list[str]) -> None:
    for plugin in plugins:
        skill_root = plugin / "skills"
        actual = {
            path.parent.name for path in skill_root.glob("*/SKILL.md") if path.is_file()
        }
        listed = documented_skills(plugin / "README.md")
        if listed != actual:
            errors.append(
                f"plugins/{plugin.name}/README.md 스킬 목록 불일치: "
                f"listed={sorted(listed)}, actual={sorted(actual)}"
            )

        for skill_path in sorted(skill_root.glob("*/SKILL.md")):
            text = skill_path.read_text(encoding="utf-8")
            relative = skill_path.relative_to(ROOT)
            if not text.startswith("---\n"):
                errors.append(f"{relative}: YAML frontmatter가 없음")
                continue
            try:
                frontmatter = text.split("---", 2)[1]
            except IndexError:
                errors.append(f"{relative}: YAML frontmatter가 닫히지 않음")
                continue
            name_match = re.search(r"(?m)^name:\s*([^\n]+)$", frontmatter)
            if not name_match:
                errors.append(f"{relative}: frontmatter `name`이 없음")
            elif name_match.group(1).strip(' \"\'') != skill_path.parent.name:
                errors.append(f"{relative}: name이 디렉터리명과 다름")
            if not re.search(r"(?m)^description:\s*(?:.+|[>|])$", frontmatter):
                errors.append(f"{relative}: frontmatter `description`이 없음")

    for path in sorted(PLUGINS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for token in BANNED_RUNTIME_TOKENS:
            if token in text:
                errors.append(f"{path.relative_to(ROOT)}: 금지 런타임 토큰 `{token}` 잔존")


def main() -> int:
    errors: list[str] = []
    plugins = plugin_dirs()
    validate_manifests(plugins, errors)
    validate_marketplaces(plugins, errors)
    validate_skills(plugins, errors)

    if errors:
        print("Consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    skill_count = sum(1 for plugin in plugins for _ in (plugin / "skills").glob("*/SKILL.md"))
    print(f"Consistency check passed: {len(plugins)} plugins, {skill_count} skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
